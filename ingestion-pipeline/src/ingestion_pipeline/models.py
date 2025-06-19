import re
from typing import List, Optional

from pydantic import BaseModel


class BaseSourceModel(BaseModel):
    name: str
    version: str
    source: str
    embedding_model: str
    vector_db_name: Optional[str] = None

    def k8s_name(self, max_length: int = 253) -> str:
        name = '-'.join((self.name, self.version, self.source)).lower()
        name = re.sub(r'[^a-z0-9-]', '-', name)
        name = re.sub(r'-+', '-', name)
        if len(name) > max_length:
            name = name[:max_length].rstrip('-')
        name = re.sub(r'^[^a-z0-9]+', '', name)
        name = re.sub(r'[^a-z0-9]+$', '', name)
        return name

    def set_vector_db_name(self):
        if self.vector_db_name is None:
            self.vector_db_name = f"{self.name}-v{self.version}".replace(" ", "-").replace(".", "-")


class GitHubSource(BaseSourceModel):
    url: str
    path: str
    token: str
    branch: str


class S3Source(BaseSourceModel):
    access_key_id: str
    secret_access_key: str
    endpoint_url: str
    bucket_name: str
    region: str


class URLsSource(BaseSourceModel):
    urls: List[str]
