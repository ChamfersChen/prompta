from http import HTTPStatus
from dashscope.audio.asr import Transcription
from urllib import request
import dashscope
import os
import json

from loguru import logger


dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

def audio2text(filepath):
    task_response = Transcription.async_call(
        model='fun-asr',
        file_urls=[filepath],
        language_hints=['zh', 'en']
    )
    Transcription.fetch

    transcription_response = Transcription.wait(task=task_response.output.task_id)
    if transcription_response.status_code == HTTPStatus.OK:
        for transcription in transcription_response.output['results']:
            if transcription['subtask_status'] == 'SUCCEEDED':
                url = transcription['transcription_url']
                result = json.loads(request.urlopen(url).read().decode('utf8'))
                return result
            else:
                logger.error(f'transcription failed! \n{transcription}')
                return None
    else:
        logger.error(f'Error: {transcription_response.output.message}')
        return None
