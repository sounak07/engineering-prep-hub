# when child classes implementing similar logic that is different
# from parent which will cause code duplication

# Storage Provider Strategy implementations

from abc import abstractmethod, ABC


class StorageStrategy(ABC):
    @abstractmethod
    def request_data(file_name: str):
        pass


class AWSStrategy(StorageStrategy):
    def request_data(self, file_name: str):
        print(f"This is getting file from AWS {file_name}")


class GCPStrategy(StorageStrategy):
    def request_data(self, file_name: str):
        print(f"This is getting file from GCP {file_name}")



class RedisStrategy(StorageStrategy):
    def request_data(self, file_name: str):
        print(f"This is getting file from Redis {file_name}")


class Storage:
    def __init__(self, strategy: StorageStrategy)  -> None:
        self.storage_strategy: StorageStrategy = strategy

    def get_data(self, file_name: str):
        self.storage_strategy.request_data(file_name)






def main():
    aws: Storage = Storage(AWSStrategy())
    aws.get_data("secret_file.sec")

    gcp: Storage = Storage(GCPStrategy())
    gcp.get_data("secret_file.sec")

    redis: Storage = Storage(RedisStrategy())
    redis.get_data("secret_file.sec")


main()