"""
Tests for XBlock handlers for the ORA MFE BFF
"""
from contextlib import contextmanager
import json
from unittest.mock import patch
from submissions import api as submission_api
from openassessment.xblock.test.base import XBlockHandlerTestCase, scenario
from openassessment.xblock.ui_mixins.mfe.constants import ErrorCodes
from openassessment.xblock.apis.submissions.errors import (
    SubmissionValidationException,
    DraftSaveException,
    StudioPreviewException,
    MultipleSubmissionsException,
    AnswerTooLongException,
    EmptySubmissionError,
    SubmitInternalError
)


def assert_error_response(response, status_code, error_code, context=''):
    assert response.status_code == status_code
    assert response.json['error'] == {
        'error_code': error_code,
        'error_context': context
    }


def assert_called_once_with_helper(mock, expected_first_arg, expected_additional_args):
    mock.assert_called_once()
    assert mock.call_args.args[0] == expected_first_arg
    assert len(mock.call_args.args) == expected_additional_args + 1
    assert not mock.call_args.kwargs


class SubmissionDraftTest(XBlockHandlerTestCase):
    RESPONSE = {'response': {'text_responses': ['hi']}}
    RESPONSE_JSON = json.dumps(RESPONSE)

    def request_save_draft(self, xblock, payload=None):
        if payload is None:
            payload = self.RESPONSE_JSON
        return super().request(
            xblock,
            'submission',
            payload,
            suffix='draft',
            response_format='response'
        )

    @contextmanager
    def _mock_save_submission_draft(self, **kwargs):
        with patch('openassessment.xblock.ui_mixins.mfe.mixin.submissions_actions') as mock_submission_actions:
            mock_submission_actions.save_submission_draft.configure_mock(**kwargs)
            yield mock_submission_actions.save_submission_draft

    @scenario("data/basic_scenario.xml")
    def test_incorrect_params(self, xblock):
        resp = self.request_save_draft(xblock, '{}')
        assert_error_response(resp, 400, ErrorCodes.INCORRECT_PARAMETERS)

    @scenario("data/basic_scenario.xml")
    def test_submission_validation_error(self, xblock):
        with self._mock_save_submission_draft(side_effect=SubmissionValidationException()):
            resp = self.request_save_draft(xblock)
        assert_error_response(resp, 400, ErrorCodes.INVALID_RESPONSE_SHAPE)

    @scenario("data/basic_scenario.xml")
    def test_draft_save_exception(self, xblock):
        with self._mock_save_submission_draft(side_effect=DraftSaveException()):
            resp = self.request_save_draft(xblock)
        assert_error_response(resp, 500, ErrorCodes.INTERNAL_EXCEPTION)

    @scenario("data/basic_scenario.xml")
    def test_draft_save(self, xblock):
        with self._mock_save_submission_draft() as mock_draft:
            resp = self.request_save_draft(xblock)
            assert resp.status_code == 200
            assert_called_once_with_helper(mock_draft, self.RESPONSE['response']['text_responses'], 2)


class SubmissionCreateTest(XBlockHandlerTestCase):
    RESPONSE = {'response': {'text_responses': ['Hello World', 'Goodbye World']}}
    RESPONSE_JSON = json.dumps(RESPONSE)

    def request_create_submission(self, xblock, payload=None):
        if payload is None:
            payload = self.RESPONSE_JSON
        return super().request(
            xblock,
            'submission',
            payload,
            suffix='create',
            response_format='response'
        )

    @contextmanager
    def _mock_create_submission(self, **kwargs):
        with patch('openassessment.xblock.ui_mixins.mfe.mixin.submissions_actions') as mock_submission_actions:
            mock_submission_actions.submit.configure_mock(**kwargs)
            yield mock_submission_actions.submit

    @scenario("data/basic_scenario.xml")
    def test_incorrect_params(self, xblock):
        resp = self.request_create_submission(xblock, '{}')
        assert_error_response(resp, 400, ErrorCodes.INCORRECT_PARAMETERS)

    @scenario("data/basic_scenario.xml")
    def test_submission_validation_exception(self, xblock):
        err_msg = 'some error message'
        with self._mock_create_submission(side_effect=SubmissionValidationException(err_msg)):
            resp = self.request_create_submission(xblock)
        assert_error_response(resp, 400, ErrorCodes.INVALID_RESPONSE_SHAPE, err_msg)

    @scenario("data/basic_scenario.xml")
    def test_in_studio_preview(self, xblock):
        with self._mock_create_submission(side_effect=StudioPreviewException()):
            resp = self.request_create_submission(xblock)
        assert_error_response(resp, 400, ErrorCodes.IN_STUDIO_PREVIEW)

    @scenario("data/basic_scenario.xml")
    def test_multiple_submissions(self, xblock):
        with self._mock_create_submission(side_effect=MultipleSubmissionsException()):
            resp = self.request_create_submission(xblock)
        assert_error_response(resp, 400, ErrorCodes.MULTIPLE_SUBMISSIONS)

    @scenario("data/basic_scenario.xml")
    def test_answer_too_long(self, xblock):
        with self._mock_create_submission(side_effect=AnswerTooLongException()):
            resp = self.request_create_submission(xblock)
        assert_error_response(resp, 400, ErrorCodes.SUBMISSION_TOO_LONG, {'maxsize': submission_api.Submission.MAXSIZE})

    @scenario("data/basic_scenario.xml")
    def test_submission_error(self, xblock):
        mock_error = submission_api.SubmissionRequestError(
            'there was a problem',
            {'answer': 'invalid format'},
        )
        with self._mock_create_submission(side_effect=mock_error):
            resp = self.request_create_submission(xblock)
        assert_error_response(resp, 400, ErrorCodes.SUBMISSION_API_ERROR, str(mock_error))

    @scenario("data/basic_scenario.xml")
    def test_empty_submission(self, xblock):
        with self._mock_create_submission(side_effect=EmptySubmissionError()):
            resp = self.request_create_submission(xblock)
        assert_error_response(resp, 400, ErrorCodes.EMPTY_ANSWER)

    @scenario("data/basic_scenario.xml")
    def test_internal_error(self, xblock):
        with self._mock_create_submission(side_effect=SubmitInternalError()):
            resp = self.request_create_submission(xblock)
        assert_error_response(resp, 500, ErrorCodes.UNKNOWN_ERROR)

    @scenario("data/basic_scenario.xml")
    def test_create_submission(self, xblock):
        with self._mock_create_submission() as mock_submit:
            resp = self.request_create_submission(xblock)
            assert resp.status_code == 200
            assert_called_once_with_helper(mock_submit, self.RESPONSE, 3)
