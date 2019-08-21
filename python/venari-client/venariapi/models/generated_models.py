from enum import IntEnum
from typing import List
from  dateutil.parser import parse


class DBType(IntEnum):
    Global_ = 0
    Job = 1
    WorkSpace = 2

    def __str__(self):
        return '%s' % self.name



class JobComparison(IntEnum):
    Same = 0
    MissingFindings = 1
    ExtraFindings = 2
    MissingAndExtraFindings = 3

    def __str__(self):
        return '%s' % self.name



class Severity(IntEnum):
    Critical = 0
    High = 1
    Medium = 2
    Low = 3
    Info = 4

    def __str__(self):
        return '%s' % self.name



class JobStatus(IntEnum):
    Ready = 0
    Acquired = 1
    Running = 2
    Paused = 3
    Completed = 4
    Resume = 5
    Failed = 6
    Cancelled = 7

    def __str__(self):
        return '%s' % self.name



class DBData(object):

    def __init__ (self,
                  db_id: str,
                  db_type: DBType):
        self.db_id: str = db_id
        self.db_type: DBType = db_type

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['DBID'], data['DBType'])


class OperationResult(object):

    def __init__ (self,
                  succeeded: bool,
                  message: str):
        self.succeeded: bool = succeeded
        self.message: str = message

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['Succeeded'], data['Message'])


class CloseDownloadStream(object):

    def __init__ (self,
                  file_id: str,
                  discard_entry: bool,
                  delete_file: bool,
                  delete_directory: bool):
        self.file_id: str = file_id
        self.discard_entry: bool = discard_entry
        self.delete_file: bool = delete_file
        self.delete_directory: bool = delete_directory

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['FileID'],
                   data['DiscardEntry'],
                   data['DeleteFile'],
                   data['DeleteDirectory'])


class CreateDownloadStream(object):

    def __init__ (self,
                  file_id: str,
                  part_size: int,
                  note: str):
        self.file_id: str = file_id
        self.part_size: int = part_size
        self.note: str = note

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['FileID'], data['PartSize'], data['Note'])


class CreateUploadStream(object):

    def __init__ (self,
                  file_name: str,
                  note: str,
                  expected_hash_hex: str):
        self.file_name: str = file_name
        self.note: str = note
        self.expected_hash_hex: str = expected_hash_hex

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['FileName'], data['Note'], data['ExpectedHashHex'])


class DetachFile(object):

    def __init__ (self,
                  file_id: str,
                  delete_file: bool,
                  delete_directory: bool):
        self.file_id: str = file_id
        self.delete_file: bool = delete_file
        self.delete_directory: bool = delete_directory

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['FileID'], data['DeleteFile'], data['DeleteDirectory'])


class DiscardFileEntry(object):

    def __init__ (self,
                  file_id: str,
                  delete_file: bool,
                  delete_directory: bool):
        self.file_id: str = file_id
        self.delete_file: bool = delete_file
        self.delete_directory: bool = delete_directory

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['FileID'], data['DeleteFile'], data['DeleteDirectory'])


class DownloadFilePart(object):

    def __init__ (self,
                  error_message: str,
                  bytes,
                  expected_hash_hex: str):
        self.error_message: str = error_message
        self.bytes = bytes
        self.expected_hash_hex: str = expected_hash_hex

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['ErrorMessage'], data['Bytes'], data['ExpectedHashHex'])


class DownloadStream(object):

    def __init__ (self,
                  error_message: str,
                  total_bytes: int,
                  part_size: int,
                  part_count: int,
                  expected_hash_hex: str):
        self.error_message: str = error_message
        self.total_bytes: int = total_bytes
        self.part_size: int = part_size
        self.part_count: int = part_count
        self.expected_hash_hex: str = expected_hash_hex

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['ErrorMessage'],
                   data['TotalBytes'],
                   data['PartSize'],
                   data['PartCount'],
                   data['ExpectedHashHex'])


class File(object):

    def __init__ (self,
                  file: str,
                  note: str):
        self.file: str = file
        self.note: str = note

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['File'], data['Note'])


class GetFilePart(object):

    def __init__ (self,
                  file_id: str,
                  part_index: int):
        self.file_id: str = file_id
        self.part_index: int = part_index

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['FileID'], data['PartIndex'])


class UploadFilePart(object):

    def __init__ (self,
                  file_id: str,
                  index: int,
                  bytes,
                  expected_hash_hex: str):
        self.file_id: str = file_id
        self.index: int = index
        self.bytes = bytes
        self.expected_hash_hex: str = expected_hash_hex

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['FileID'],
                   data['Index'],
                   data['Bytes'],
                   data['ExpectedHashHex'])


class ExportFindings(object):

    def __init__ (self,
                  workspace_db_name: str,
                  job_unique_id: str):
        self.workspace_db_name: str = workspace_db_name
        self.job_unique_id: str = job_unique_id

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['WorkspaceDbName'], data['JobUniqueID'])


class ExportFindingsResult(object):

    def __init__ (self,
                  error_message: str,
                  file_id: str):
        self.error_message: str = error_message
        self.file_id: str = file_id

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['ErrorMessage'], data['FileID'])


class ImportFindings(object):

    def __init__ (self,
                  job_unique_id: str,
                  DBData: DBData,
                  workspace_name: str,
                  file_id: str):
        self.job_unique_id: str = job_unique_id
        self.DBData: DBData = DBData
        self.workspace_name: str = workspace_name
        self.file_id: str = file_id

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['JobUniqueID'],
                   data['DBData'],
                   data['WorkspaceName'],
                   data['FileID'])


class JobCompareResult(object):

    def __init__ (self,
                  workspace_db_name: str,
                  error_message: str,
                  comparison: JobComparison,
                  display_details: str,
                  missing_findings_count: int,
                  extra_findings_count: int):
        self.workspace_db_name: str = workspace_db_name
        self.error_message: str = error_message
        self.comparison: JobComparison = comparison
        self.display_details: str = display_details
        self.missing_findings_count: int = missing_findings_count
        self.extra_findings_count: int = extra_findings_count

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['WorkspaceDbName'],
                   data['ErrorMessage'],
                   data['Comparison'],
                   data['DisplayDetails'],
                   data['MissingFindingsCount'],
                   data['ExtraFindingsCount'])


class JobTemplate(object):

    def __init__ (self,
                  id: int,
                  version: int,
                  unique_id: str,
                  name: str,
                  settings_type: str,
                  settings_type_display_name: str,
                  settings_id: int,
                  created_at):
        self.id: int = id
        self.version: int = version
        self.unique_id: str = unique_id
        self.name: str = name
        self.settings_type: str = settings_type
        self.settings_type_display_name: str = settings_type_display_name
        self.settings_id: int = settings_id
        self.created_at: str = created_at

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['ID'],
                   data['Version'],
                   data['UniqueID'],
                   data['Name'],
                   data['SettingsType'],
                   data['SettingsTypeDisplayName'],
                   data['SettingsID'],
                   None if not data['CreatedAt'] else parse(data['CreatedAt']))
