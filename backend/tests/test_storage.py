from unittest.mock import patch, MagicMock
from src.storage import upload_image, download_image, save_result

FAKE_PUBLIC_URL = "https://storage.googleapis.com/dal-i-bucket/images/test.jpg"


def _make_mock_client(public_url: str = FAKE_PUBLIC_URL):
    """Return a mock storage.Client with a pre-configured blob."""
    mock_blob = MagicMock()
    mock_blob.public_url = public_url
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_client = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    return mock_client, mock_bucket, mock_blob


# ---------------------------------------------------------------------------
# upload_image
# ---------------------------------------------------------------------------

@patch("src.storage.storage.Client")
def test_upload_image_returns_public_url(MockClient, sample_image_bytes):
    mock_client, mock_bucket, mock_blob = _make_mock_client()
    MockClient.return_value = mock_client

    url = upload_image(sample_image_bytes, "test.jpg", "image/jpeg")

    assert url == FAKE_PUBLIC_URL
    mock_bucket.blob.assert_called_once_with("images/test.jpg")
    mock_blob.upload_from_string.assert_called_once_with(sample_image_bytes, content_type="image/jpeg")
    mock_blob.make_public.assert_called_once()


@patch("src.storage.storage.Client")
def test_upload_image_default_content_type(MockClient, sample_image_bytes):
    mock_client, _, mock_blob = _make_mock_client()
    MockClient.return_value = mock_client

    upload_image(sample_image_bytes, "test.jpg")

    _, kwargs = mock_blob.upload_from_string.call_args
    assert kwargs.get("content_type") == "image/jpeg"


# ---------------------------------------------------------------------------
# download_image
# ---------------------------------------------------------------------------

@patch("src.storage.storage.Client")
def test_download_image_returns_bytes(MockClient, sample_image_bytes):
    mock_client, mock_bucket, mock_blob = _make_mock_client()
    mock_blob.download_as_bytes.return_value = sample_image_bytes
    MockClient.return_value = mock_client

    result = download_image("test.jpg")

    assert result == sample_image_bytes
    mock_bucket.blob.assert_called_once_with("images/test.jpg")
    mock_blob.download_as_bytes.assert_called_once()


# ---------------------------------------------------------------------------
# save_result
# ---------------------------------------------------------------------------

@patch("src.storage.storage.Client")
def test_save_result_returns_public_url(MockClient):
    result_url = "https://storage.googleapis.com/dal-i-bucket/results/out.json"
    mock_client, mock_bucket, mock_blob = _make_mock_client(result_url)
    MockClient.return_value = mock_client

    payload = '{"coordinates": [{"x": 1.0, "y": 2.0}]}'
    url = save_result(payload, "out.json")

    assert url == result_url
    mock_bucket.blob.assert_called_once_with("results/out.json")
    mock_blob.upload_from_string.assert_called_once_with(payload, content_type="application/json")
    mock_blob.make_public.assert_called_once()
