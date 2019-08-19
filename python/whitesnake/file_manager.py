from venariapi.models import *
from models import TestData, RegressionExecResult, TestExecResult
from venariapi import VenariAuth, VenariApi, VenariAuth
import venariapi.examples.credentials as creds
import time
import datetime
import sys
from pathlib import Path
import hashlib;
import base64
import os

class FileManagerClient(object):

    def __init__ (self, master_node: str):
        self._master_node = master_node
        self._api = None
        self._part_size = 64000


    def connect(self, auth: VenariAuth):
        self._api = VenariApi(auth, self._master_node)


    def hash_file_bytes_to_md5_hex(self, file) -> str:
        hash = hashlib.md5()
        with open(file, "rb") as f:
            for part in iter(lambda: f.read(4096), b""):
                hash.update(part)
        return hash.hexdigest()


    def hash_bytes_to_md5_hex(self, bytes) -> str:
        result = hashlib.md5(bytes) 
        return result.digest().hex()


    def upload_file(self, file: str, note: str) -> str:

        # create an upload stream object on the server
        hash = self.hash_file_bytes_to_md5_hex(file)
        file_name = os.path.basename(file)
        file_id = self._api.create_upload_stream(file_name, note, hash)
        if (not file_id):
            return None

        # upload the parts
        try:
            with open(file, 'rb') as f:
                index = 0
                for part in self._read_in_parts(f, self._part_size):
                    uploaded = self._upload_part(file_id, part, index)
                    if (not uploaded):
                        return False

                    index += 1

            return file_id

        finally:
            # close the stream
            self._api.close_upload_stream(file_id)


    def download_file(self, target_file: str, file_id: str, note: str) -> bool:

        # create a download stream
        download_data = self._api.create_download_stream(file_id, note, self._part_size)
        if (download_data.error_message or download_data.part_count == 0 or download_data.total_bytes == 0):
            return False

        # download the parts
        try:
            i = 0
            with open(target_file,'wb') as f:
                while (i < download_data.part_count):
                    bytes = self._download_part(file_id, i)
                    if (not bytes):
                        return False

                    f.write(bytes)
                    i += 1

            # file hash compare
            hash = self.hash_file_bytes_to_md5_hex(target_file)
            if (hash != download_data.expected_hash_hex):
                return False

            return True

        finally:
            # close the stream
            self._api.close_download_stream(file_id, True, True, True)


    def _download_part(self, file_id: str, index: int):
        for i in range(0,2):
            try:
                part = self._api.download_file_part(file_id, index)
                if (part.error_message):
                    continue
                bytes = base64.b64decode(part.bytes)
                if (part.expected_hash_hex):
                    actual_hash = self.hash_bytes_to_md5_hex(bytes)
                    if (actual_hash.lower() != part.expected_hash_hex.lower()):
                        continue
                
                return bytes

            except:
                type, value, traceback = sys.exc_info()
                continue

        return None



    def _upload_part(self, file_id: str, bytes, index: int) -> bool:
        for i in range(0,2):
            part_hash = self.hash_bytes_to_md5_hex(bytes)
            try:
                result = self._api.upload_file_part(file_id, index, bytes, part_hash)
                if (result.succeeded):
                    return True
            except:
                type, value, traceback = sys.exc_info()
                continue

        return False


    def _read_in_parts(self, file_object, part_size):
        while True:
            data = file_object.read(part_size)
            if not data:
                break
            yield data



if __name__ == '__main__':

    master_node = "https://host.docker.internal:9000"
    file_manager = FileManagerClient(master_node)

    # connect to the master node
    auth = creds.load_credentials(master_node)
    file_manager.connect(auth);
    upload_file = "C:/Users/Steve/Desktop/Sequoia Pitch Template.pdf"
    target_file = "C:/Users/Steve/Desktop/round-trip-copy-of-Sequoia Pitch Template.pdf"

    file_id = file_manager.upload_file(upload_file, "upload test")
    result = file_manager.download_file(target_file, file_id, "download test")