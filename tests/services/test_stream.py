import json
from unittest.mock import MagicMock
from app.services.stream import publish_upload_job, create_consumer_group, get_job_status, save_job_status, STREAM_KEY, CONSUMER_GROUP

def test_publish_upload_job(mock_redis):
    document_id = "test-doc"
    file_name = "test.pdf"
    temp_path = "/tmp/test.pdf"
    
    job_id = publish_upload_job(document_id, file_name, temp_path)
    
    assert job_id is not None
    mock_redis.xadd.assert_called_once()
    args = mock_redis.xadd.call_args[0]
    assert args[0] == STREAM_KEY
    assert args[1]["document_id"] == document_id
    assert args[1]["job_id"] == job_id

def test_create_consumer_group_new(mock_redis):
    create_consumer_group()
    mock_redis.xgroup_create.assert_called_once_with(STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True)

def test_create_consumer_group_exists(mock_redis, mocker):
    mock_redis.xgroup_create.side_effect = Exception("BUSYGROUP Consumer Group name already exists")
    mock_logger = mocker.patch("app.services.stream.logger")
    
    create_consumer_group()
    
    mock_logger.info.assert_called_with(f"Consumer group {CONSUMER_GROUP} already exists")

def test_save_and_get_job_status(mock_redis):
    job_id = "job-123"
    status = "completed"
    message = "Done"
    
    save_job_status(job_id, status, message)
    
    mock_redis.setex.assert_called_once()
    args = mock_redis.setex.call_args[0]
    assert args[0] == f"job:{job_id}"
    
    saved_data = json.loads(args[2])
    mock_redis.get.return_value = json.dumps(saved_data)
    
    retrieved = get_job_status(job_id)
    assert retrieved["status"] == status
    assert retrieved["message"] == message
