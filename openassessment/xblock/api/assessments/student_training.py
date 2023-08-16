from openassessment.assessment.api import student_training

from openassessment.xblock.data_conversion import (
    convert_training_examples_list_to_dict,
    create_submission_dict
)
from openassessment.xblock.resolve_dates import DISTANT_FUTURE
from openassessment.xblock.api.block import BlockAPI
from .problem_closed import ProblemClosedAPI

class StudentTrainingAPI:
    def __init__(self, block):
        self._raw_block = block
        self._block = BlockAPI(block)
        self._is_closed = ProblemClosedAPI(block.is_closed(step="self-assessment"))

    @property
    def is_cancelled(self):
        return self._block.workflow.is_cancelled

    @property
    def is_complete(self):
        state = self._block.workflow
        return state.has_status and not (state.is_cancelled or state.is_training)

    def has_workflow(self):
        return self._block.workflow.has_status

    @property
    def problem_closed(self):
        return self._is_closed.problem_closed

    @property
    def due_date(self):
        return self._is_closed.due_date

    @property
    def start_date(self):
        return self._is_closed.start_date

    @property
    def is_due(self):
        return self._is_closed.is_due

    @property
    def is_past_due(self):
        return self._is_closed.is_past_due

    @property
    def is_not_available_yet(self):
        return self._is_closed.is_not_available_yet

    @property
    def training_module(self):
        return self._block.get_assessment_module('student_training')

    @property
    def num_available(self):
        return len(self.training_module['examples'])

    @property
    def num_completed(self):
        return student_training.get_num_completed(self._block.submission_uuid)

    @property
    def examples(self):
        return convert_training_examples_list_to_dict(self.training_module['examples'])

    @property
    def example(self):
        return student_training.get_training_example(
            self._block.submission_uuid,
            {'prompt': self._block.prompt, 'criteria': self._block.rubric_criteria_with_labels},
            self.examples
        )

    @property
    def example_context(self):
        context, error_message = self._parse_example(self.example)
        return {
            'error_message': error_message,
            'essay_context': context
        }

    @property
    def example_rubric(self):
        rubric = self.example['rubric']
        return {'criteria': rubric['criteria'], 'points_possible': rubric['points_possible']}

    def _parse_answer_dict(self, answer):
        """
        Helper to parse answer as a fully-qualified dict.
        """
        parts = answer.get('parts', [])
        if parts and isinstance(parts[0], dict):
            if isinstance(parts[0].get('text'), str):
                return create_submission_dict({'answer': answer}, self._block.prompts)
        return None

    def _parse_answer_list(self, answer):
        """
        Helper to parse answer as a list of strings.
        """
        if answer and isinstance(answer[0], str):
            return self._parse_answer_string(answer[0])
        elif not answer:
            return self._parse_answer_string("")
        return None

    def _parse_answer_string(self, answer):
        """
        Helper to parse answer as a plain string
        """
        return create_submission_dict({'answer': {'parts': [{'text': answer}]}}, self._block.prompts)

    def _parse_example(self, example):
        """
        EDUCATOR-1263: examples are serialized in a myriad of different ways, we need to be robust to all of them.

        Types of serialized example['answer'] we handle here:
        -fully specified: {'answer': {'parts': [{'text': <response_string>}]}}
        -list of string: {'answer': [<response_string>]}
        -just a string: {'answer': <response_string>}
        """
        if not example:
            return None
        answer = example['answer']
        submission_dict = None
        if isinstance(answer, str):
            submission_dict = self._parse_answer_string(answer)
        elif isinstance(answer, dict):
            submission_dict = self._parse_answer_dict(answer)
        elif isinstance(answer, list):
            submission_dict = self._parse_answer_list(answer)
        return submission_dict