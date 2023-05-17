import datetime
import os
import time
import uuid

from django.conf import settings
from django.db import transaction

from applications.music.models import Folder, Track, Album, Genre, Artist, Attachment
from applications.subsonic.constants import AUDIO_EXTENSIONS_AND_MIMETYPE, COVER_TYPE
from applications.task.services.scan_utils import ScanMusic
from applications.task.utils import folder_update_time, exists_dir
from django_vue_cli.celery_app import app


def get_uuid():
    return str(uuid.uuid4())


@app.task
def full_scan_folder(sub_path=None):
    a = time.time()
    bulk_create = []
    music_folder = os.path.join(settings.MEDIA_ROOT, "music")
    ignore_path = [os.path.join(music_folder, "data")]
    if sub_path:
        stack = sub_path
    else:
        stack = [(None, music_folder)]
    while len(stack) != 0:
        # 从栈里取出数据
        parent_uid, dir_data = stack.pop()
        if os.path.isdir(dir_data):
            if dir_data in ignore_path:
                continue
            try:
                entries = os.scandir(dir_data)
                my_uuid = get_uuid()
            except Exception as e:
                m = f"Error while reading {dir}: {e.__class__.__name__} {e}\n"
                print(m)
                continue
            try:
                sub_path = [(my_uuid, entry.path) for entry in entries]
            except Exception as e:
                m = f"Error2 while reading {dir}: {e.__class__.__name__} {e}\n"
                print(m)
                continue
            finally:
                if hasattr(entries, "close"):
                    entries.close()

            # stack.extend(sub_path)
            if sub_path:
                full_scan_folder.delay(sub_path=sub_path)
            bulk_create.append(
                Folder(**{
                    "name": dir_data.split("/")[-1],
                    "path": dir_data,
                    "file_type": "folder",
                    "uid": my_uuid,
                    "parent_id": parent_uid
                })
            )
        else:
            suffix = dir_data.split(".")[-1]
            if suffix in dict(AUDIO_EXTENSIONS_AND_MIMETYPE):
                my_uuid = get_uuid()
                bulk_create.append(
                    Folder(**{
                        "name": dir_data.split("/")[-1],
                        "path": dir_data,
                        "file_type": "music",
                        "uid": my_uuid,
                        "parent_id": parent_uid
                    })
                )
            elif suffix in COVER_TYPE:
                my_uuid = get_uuid()
                bulk_create.append(
                    Folder(**{
                        "name": dir_data.split("/")[-1],
                        "path": dir_data,
                        "file_type": "image",
                        "uid": my_uuid,
                        "parent_id": parent_uid
                    })
                )
        if len(bulk_create) % 500 == 0:
            Folder.objects.bulk_create(bulk_create, batch_size=500)
            bulk_create = []
    if len(bulk_create) > 0:
        Folder.objects.bulk_create(bulk_create, batch_size=500)
    print("完成扫描！", time.time() - a)


@app.task
def update_scan_folder(sub_path=None):
    music_folder = os.path.join(settings.MEDIA_ROOT, "music")
    ignore_path = [os.path.join(music_folder, "data")]
    print(music_folder)
    if sub_path:
        stack = sub_path
    else:
        stack = [(None, music_folder)]
    last_folder = Folder.objects.order_by("-last_scan_time").first()
    if last_folder:
        last_scan_time = last_folder.last_scan_time
    else:
        last_scan_time = datetime.datetime(1970, 1, 1)
    now_time = datetime.datetime.now()
    while len(stack) != 0:
        # 从栈里取出数据
        parent_uid, dir_data = stack.pop(0)
        if dir_data in ignore_path:
            continue
        if os.path.isdir(dir_data):
            try:
                sub_path = os.scandir(dir_data)
            except Exception as e:
                m = f"Error3 while reading {dir}: {e.__class__.__name__} {e}\n"
                print(m)
                continue
            update_time = folder_update_time(dir_data)
            if update_time < last_scan_time:
                try:
                    sub_path_list = [i.path for i in sub_path]
                except Exception as e:
                    m = f"Error4 while reading {dir}: {e.__class__.__name__} {e}\n"
                    print(m)
                    continue
                finally:
                    if hasattr(sub_path, "close"):
                        sub_path.close()
                if not exists_dir(sub_path_list):
                    continue
            current_folder = Folder.objects.filter(path=dir_data).first()
            if current_folder:
                my_uuid = current_folder.uid
                update_data = {
                    "name": dir_data.split("/")[-1],
                    "file_type": "folder",
                    "uid": my_uuid,
                    "parent_id": parent_uid,
                    "updated_at": now_time,
                }
            else:
                my_uuid = get_uuid()
                update_data = {
                    "name": dir_data.split("/")[-1],
                    "file_type": "folder",
                    "uid": my_uuid,
                    "parent_id": parent_uid,
                    "updated_at": now_time,
                }
            Folder.objects.update_or_create(path=dir_data, defaults=update_data)
            try:
                sub_path = [(my_uuid, f"{dir_data}/{i}") for i in sub_path]
            except Exception as e:
                m = f"Error5 while reading {dir}: {e.__class__.__name__} {e}\n"
                print(m)
                continue
            finally:
                if hasattr(sub_path, "close"):
                    sub_path.close()
            # stack.extend(sub_path)
            if sub_path:
                update_scan_folder.delay(sub_path)
        else:
            suffix = dir_data.split(".")[-1]
            if suffix in dict(AUDIO_EXTENSIONS_AND_MIMETYPE):
                print(dir_data)
                my_uuid = get_uuid()
                update_data = {
                    "name": dir_data.split("/")[-1],
                    "file_type": "music",
                    "uid": my_uuid,
                    "parent_id": parent_uid,
                    "updated_at": now_time,
                    "state": "updated"
                }
            elif suffix in COVER_TYPE:
                my_uuid = get_uuid()
                update_data = {
                    "name": dir_data.split("/")[-1],
                    "file_type": "image",
                    "uid": my_uuid,
                    "parent_id": parent_uid,
                    "updated_at": now_time,
                    "state": "updated"
                }
            else:
                continue
            Folder.objects.update_or_create(path=dir_data, defaults=update_data)
    folder_lst = Folder.objects.filter(updated_at=now_time, file_type="folder")
    for folder in folder_lst:
        path_list = list(
            Folder.objects.filter(parent_id=folder.uid).exclude(updated_at=now_time).values_list("path", flat=True))
        with transaction.atomic():
            Track.objects.filter(path__in=path_list).delete()
            Folder.objects.filter(parent_id=folder.uid).exclude(updated_at=now_time).delete()

    print("完成更新扫描！")


@app.task
def scan_folder():
    if Folder.objects.count() > 0:
        update_scan_folder()
    else:
        full_scan_folder()


@app.task
def scan_music_id3():
    a = time.time()
    ScanMusic("/").scan()
    print(time.time() - a)


@app.task
def scan():
    if Folder.objects.count() > 0:
        update_scan_folder()
    else:
        full_scan_folder()
    ScanMusic("/").scan()


def clear_music():
    Folder.objects.all().delete()
    Track.objects.all().delete()
    Album.objects.all().delete()
    Genre.objects.all().delete()
    Artist.objects.all().delete()
    Attachment.objects.all().delete()