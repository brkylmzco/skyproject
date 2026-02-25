from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .device_registration import DeviceRegistrationService
from skyproject.shared.logging_utils import log_error, log_info, ErrorCode

app = FastAPI()

class DeviceRegistrationRequest(BaseModel):
    user_id: str
    token: str
    platform: str

@app.post('/api/register-device')
async def register_device(request: DeviceRegistrationRequest):
    success = DeviceRegistrationService.register_device(request.user_id, request.token, request.platform)
    if not success:
        log_error(ErrorCode.DEVICE_REGISTRATION_FAILED, f'Failed to register device: {request}')
        raise HTTPException(status_code=500, detail='Failed to register device')
    log_info(f'Device registered successfully: {request}')
    return {'message': 'Device registered successfully'}

@app.get('/api/tokens')
async def get_tokens():
    try:
        tokens = DeviceRegistrationService.get_all_tokens()
        log_info('Retrieved tokens successfully')
        return {'tokens': tokens}
    except Exception as e:
        log_error(ErrorCode.TOKEN_RETRIEVAL_ERROR, f'Error retrieving tokens: {str(e)}')
        raise HTTPException(status_code=500, detail='Error retrieving tokens')
