"""
Data layer for ORA

XBlock handlers which surface info about an ORA, instead of being tied to views.
"""
from xblock.core import XBlock
from xblock.exceptions import JsonHandlerError

from submissions.api import get_submission
from submissions.team_api import get_team_submission

from openassessment.data import OraSubmissionAnswerFactory
from openassessment.xblock.apis.submissions import submissions_actions
from openassessment.xblock.apis.submissions.errors import (
    SubmissionValidationException,
    DraftSaveException,
    StudioPreviewException,
    MultipleSubmissionsException,
    AnswerTooLongException,
    EmptySubmissionError,
    SubmitInternalError,
)
from openassessment.xblock.ui_mixins.mfe.constants import ErrorCodes
from openassessment.xblock.ui_mixins.mfe.serializers import (
    GetBlockLearnerSubmissionDataSerializer,
    OraBlockInfoSerializer,
)
from openassessment.xblock.utils.data_conversion import create_submission_dict


class OraApiException(JsonHandlerError):
    def __init__(self, status_code, error_code, error_context=''):
        super().__init__(
            status_code,
            {
                'error_code': error_code,
                'error_context': error_context
            }
        )


class MfeMixin:
    @XBlock.json_handler
    def get_block_info(self, data, suffix=""):  # pylint: disable=unused-argument
        block_info = OraBlockInfoSerializer(self)
        return block_info.data

    def get_submission(self, submission_uuid):
        """
        Get a serialized representation of an ORA submission.
        Returns:
            {
                "text_responses": (list) [text responses]
                "uploaded_files": (list) [
                    {
                        "download_url": (url)
                        "description": (str)
                        "name": (str)
                        "size": (int)
                    }
                ]
            }

        Raises:
            submissions.errors.SubmissionError: If there was an error loading the submission
            openassessment.data.VersionNotFoundException: If the submission did not match any known
                                                          ORA answer version
        """
        if self.is_team_assignment():
            submission = get_team_submission(submission_uuid)
        else:
            submission = get_submission(submission_uuid)
        return OraSubmissionAnswerFactory.parse_submission_raw_answer(submission.get('answer'))

    def _submission_draft(self, data):
        try:
            student_submission_data = data['response']['text_responses']
            submissions_actions.save_submission_draft(student_submission_data, self.config_data, self.submission_data)
        except KeyError as e:
            raise OraApiException(400, ErrorCodes.INCORRECT_PARAMETERS) from e
        except SubmissionValidationException as exc:
            raise OraApiException(400, ErrorCodes.INVALID_RESPONSE_SHAPE, str(exc)) from exc
        except DraftSaveException as e:
            raise OraApiException(500, ErrorCodes.INTERNAL_EXCEPTION) from e

    def _submission_create(self, data):
        from submissions import api as submission_api
        try:
            submissions_actions.submit(data, self.config_data, self.submission_data, self.workflow_data)
        except KeyError as e:
            raise OraApiException(400, ErrorCodes.INCORRECT_PARAMETERS) from e
        except SubmissionValidationException as e:
            raise OraApiException(400, ErrorCodes.INVALID_RESPONSE_SHAPE, str(e)) from e
        except StudioPreviewException as e:
            raise OraApiException(400, ErrorCodes.IN_STUDIO_PREVIEW) from e
        except MultipleSubmissionsException as e:
            raise OraApiException(400, ErrorCodes.MULTIPLE_SUBMISSIONS) from e
        except AnswerTooLongException as e:
            raise OraApiException(400, ErrorCodes.SUBMISSION_TOO_LONG, {
                'maxsize': submission_api.Submission.MAXSIZE
            }) from e
        except submission_api.SubmissionRequestError as e:
            raise OraApiException(400, ErrorCodes.SUBMISSION_API_ERROR, str(e)) from e
        except EmptySubmissionError as e:
            raise OraApiException(400, ErrorCodes.EMPTY_ANSWER) from e
        except SubmitInternalError as e:
            raise OraApiException(500, ErrorCodes.UNKNOWN_ERROR, str(e)) from e

    @XBlock.json_handler
    def submission(self, data, suffix=""):
        if suffix == 'draft':
            return self._submission_draft(data)
        elif suffix == "create":
            return self._submission_create(data)
        else:
            raise OraApiException(404, ErrorCodes.UNKNOWN_SUFFIX)

    def get_submission_team_info(self, workflow):
        if not self.is_team_assignment():
            return {}, None

        team_info = self.get_team_info(staff_or_preview_data=False)
        if team_info is None:
            team_info = {}

        # Get the id of the team the learner is currently on
        team_id = team_info.get('team_id', None)
        if team_id:
            # Has the team the learner is currently on already submitted?
            team_info['has_submitted'] = self.does_team_have_submission(team_id)

        if workflow:
            # If the learner has submitted, use the team id on the learner's submission later
            # for shared files lookup. If the learner has submitted already for a different team
            # and then joined another team, we should show the submission that they are actually a part of,
            # rather than just their current team. If they have a submission (and therefore a workflow) then
            # that takes precidence.
            team_submission = get_team_submission(workflow['team_submission_uuid'])
            team_id = team_submission['team_id']
        return team_info, team_id

    def get_in_progress_file_upload_data(self, team_id=None):
        if not self.file_upload_type:
            return []
        return self.file_manager.file_descriptors(team_id=team_id, include_deleted=True)

    def get_in_progress_team_file_upload_data(self, team_id=None):
        if not self.file_upload_type or not self.is_team_assignment():
            return []
        return self.file_manager.team_file_descriptors(team_id=team_id, include_deleted=True)

    @XBlock.json_handler
    def get_block_learner_submission_data(self, data, suffix=""):  # pylint: disable=unused-argument
        workflow = self.get_team_workflow_info() if self.teams_enabled else self.get_workflow_info()
        team_info, team_id = self.get_submission_team_info(workflow)

        # If there is a submission, we do not need to load file upload data seprately because files
        # will already have been gathered into the submission. If there is no submission, we need to
        # load file data from learner state and the SharedUpload db model
        if workflow:
            response = self.get_submission(workflow.identifying_uuid)
            file_data = []
        else:
            response = create_submission_dict(self.formatted_saved_response, self.prompts)
            file_data = self.get_in_progress_file_upload_data(team_id)
            team_info['team_uploaded_files'] = self.get_in_progress_team_file_upload_data(team_id)

        data = {
            'workflow': {
                'has_submitted': bool(workflow),
                'has_cancelled': workflow.is_cancelled,
                'has_recieved_grade': bool(workflow.score),
            },
            'team_info': team_info,
            'response': response,
            'file_data': file_data,
        }
        return GetBlockLearnerSubmissionDataSerializer(data).data
