import json
import logging
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_client():
    """S3 클라이언트 생성 — 자격증명이 있으면 명시적으로, 없으면 IAM Role 사용"""
    kwargs = {"region_name": settings.aws_region}
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("s3", **kwargs)


def upload_json(cognito_id: str, filename: str, data: dict) -> str:
    """
    JSON 데이터를 S3에 업로드한다.
    — key: health-data/{cognito_id}/{filename}
    — 실패 시 예외를 발생시키지 않고 경고 로그만 남김 (데이터 조회 흐름을 막지 않기 위해)
    """
    key = f"health-data/{cognito_id}/{filename}"
    try:
        client = _get_client()
        client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=key,
            Body=json.dumps(data, ensure_ascii=False, default=str),
            ContentType="application/json",
        )
        logger.info("[S3] 업로드 완료: s3://%s/%s", settings.s3_bucket_name, key)
        return key
    except Exception as e:
        logger.warning("[S3] 업로드 실패 (계속 진행): %s", str(e))
        return ""


def download_json(cognito_id: str, filename: str) -> dict | None:
    """
    S3에서 JSON 데이터를 다운로드한다.
    — 파일이 없거나 실패하면 None 반환
    """
    key = f"health-data/{cognito_id}/{filename}"
    try:
        client = _get_client()
        response = client.get_object(Bucket=settings.s3_bucket_name, Key=key)
        content = response["Body"].read().decode("utf-8")
        return json.loads(content)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            logger.info("[S3] 파일 없음: %s", key)
        else:
            logger.warning("[S3] 다운로드 실패: %s", str(e))
        return None
    except Exception as e:
        logger.warning("[S3] 다운로드 실패: %s", str(e))
        return None
