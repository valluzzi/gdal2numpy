# -------------------------------------------------------------------------------
# MIT License:
# Copyright (c) 2012-2019 Luzzi Valerio
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
#
# Name:        filesystem.py
# Purpose:
#
# Author:      Luzzi Valerio
#
# Created:     16/12/2019
# -------------------------------------------------------------------------------

import datetime
import json
import os
import tempfile
import hashlib
import shutil
import random
from .module_types import parseInt, isstring, isarray
from .module_log import Logger


def now():
    """
    now
    :return: returns the time in ms
    """
    return datetime.datetime.now()


def total_seconds_from(t):
    """
    total_seconds_from
    :param t: the time in ms
    :return: return the timedelta in ms from now es now()-t
    """
    return (datetime.datetime.now() - t).total_seconds()


def normpath(pathname):
    """
    normpath
    """
    if not pathname:
        return ""
    pathname = os.path.normpath(pathname.replace("\\", "/")).replace("\\", "/")
    # patch for s3:// and http:// https://
    pathname = pathname.replace(":/", "://")
    return pathname


def juststem(pathname):
    """
    juststem
    """
    pathname = os.path.basename(pathname)
    root, _ = os.path.splitext(pathname)
    return root


def justpath(pathname, n=1):
    """
    justpath
    """
    for _ in range(n):
        pathname, _ = os.path.split(normpath(pathname))
    if pathname == "":
        return "."
    return normpath(pathname)


def justfname(pathname):
    """
    justfname - returns the basename
    """
    return normpath(os.path.basename(normpath(pathname)))


# def israster(pathname):
#     """
#     israster
#     """
#     return pathname and os.path.isfile(pathname) and justext(pathname).lower() in ("tif",)

# moved to module_s3.py
# def isshape(pathname):
#     """
#     isshape
#     """
#     return pathname and os.path.isfile(pathname) and justext(pathname).lower() in ("shp",)

def normshape(pathname):
    """
    normshape
    """
    if pathname is None:
        return None
    # sometime the shapefile is in the form s3://bucket/filename.shp|layername
    if ".shp" in pathname.lower():
        pathname = pathname.split("|", 1)[0]
    return normpath(pathname)


def parse_key_value(text, sep="="):
    """
    parse_key_value
    """
    if text is None:
        return {}
    elif isinstance(text, str):
        key, value = text.split(sep, 1)
        key, value = key.strip(), value.strip()
        if "," in value:
            value = listify(value)
        return key, value
    elif isinstance(text, (tuple, list)) and len(text) == 2:
        return text
    return None, None


def parse_shape_path(pathname):
    """
    normshape
    """
    if pathname is None:
        return None
    # sometime the shapefile is in the form 
    # s3://bucket/filename.shp|layername=filename
    # s3://bucket/filename.shp|layername=filename|fid=0
    # s3://bucket/filename.shp|layername=filename|fid=1,3,7
    parts = pathname.split("|")
    if len(parts) == 1:
        return parts[0], None, None
    elif len(parts) == 2:
        filename = parts[0]
        key, name = parse_key_value(parts[1])
        layername = name if key.lower() == "layername" else None
        fid = None
        return filename, layername, fid
    elif len(parts) == 3:
        filename = parts[0]
        key, name = parse_key_value(parts[1])
        layername = name if key.lower() == "layername" else None
        key, fid = parse_key_value(parts[2])
        if isstring(fid) and key.lower() == "fid":
            fid = parseInt(fid)   
        elif isarray(fid) and key.lower() == "fid":
            fid = [parseInt(f) for f in fid]
        return filename, layername, fid
    return None, None, None


def justext(pathname):
    """
    justext
    """
    pathname = os.path.basename(normpath(pathname))
    _, ext = os.path.splitext(pathname)
    return ext.lstrip(".")


def forceext(pathname, newext):
    """
    forceext
    """
    root, _ = os.path.splitext(normpath(pathname))
    pathname = root + ("." + newext if len(newext.strip()) > 0 else "")
    return normpath(pathname)


def filesize(filename):
    """
    filesize
    """
    if os.path.isfile(filename):
        return os.path.getsize(filename)
    else:
        return -1


def filectime(filename):
    """
    filectime - get the creation date
    """
    if os.path.exists(filename):
        unixtimestamp = os.path.getctime(filename)
        return datetime.datetime.fromtimestamp(unixtimestamp).strftime("%Y-%m-%d %H:%M:%S")
    else:
        return None


def mkdirs(pathname):
    """
    mkdirs - create a folder
    """
    try:
        if os.path.isfile(pathname):
            pathname = justpath(pathname)
        os.makedirs(pathname, exist_ok=True)
    except OSError as ex:
        Logger.error(ex)
    return os.path.isdir(pathname)


def remove(pathname):
    """
    remove - remove a file
    """
    if pathname is None:
        return
    elif isinstance(pathname, str) and os.path.isfile(pathname):
        try:
            os.remove(pathname)
        except OSError as ex:
            Logger.error(ex)
    elif isinstance(pathname, str) and os.path.isdir(pathname):
        try:
            shutil.rmtree(pathname)
        except OSError as ex:
            Logger.error(ex)
    elif isinstance(pathname, (list, tuple)):
        for filename in pathname:
            remove(filename)


def tempdir(name=""):
    """
    tempdir
    :return: a temporary directory
    """
    foldername = normpath(tempfile.gettempdir() + "/" + name)
    os.makedirs(foldername, exist_ok=True)
    return foldername


def tempfilename(prefix="", suffix=""):
    """
    return a temporary filename
    """
    r = random.randint(0, 1000)
    return normpath(f"{tempfile.gettempdir()}/{prefix}{now().strftime('%Y%m%d%H%M%S%f')}{r}{suffix}")


def strtofile(text, filename, append=False):
    """
    strtofile
    """
    try:
        flag = "a" if append else "w"
        if isinstance(text, (str,)):
            text = text.encode("utf-8")
        if isinstance(text, (bytes,)):
            flag += 'b'
        os.makedirs(justpath(filename), exist_ok=True)
        with open(filename, flag) as stream:
            if text:
                stream.write(text)
    except OSError as ex:
        Logger.error(ex)
        return ""
    return filename


def jsontofile(obj, filename):
    """
    jsontofile
    """
    return strtofile(json.dumps(obj), filename)


def filetostr(filename):
    """
    filetostr
    """
    try:
        with open(filename, "r", encoding="utf-8") as stream:
            return stream.read()
    except OSError as ex:
        Logger.error(ex)
        return None


def filetojson(filename):
    """
    filetojson
    """
    try:
        with open(filename, "r", encoding="utf-8") as stream:
            return json.load(stream)
    except OSError as ex:
        Logger.error(ex)
        return None


def listify(text, sep=",", trim=False):
    """
    listify -  make a list from string
    """
    if text is None:
        return []
    elif isinstance(text, str):
        arr = text.split(sep)
        if trim:
            arr = [item.strip() for item in arr]
        return arr
    elif isinstance(text, (tuple, list)):
        return text
    return [text]


def md5text(text):
    """
    md5text - Returns the md5 of the text
    """
    if text is not None:
        hashcode = hashlib.md5()
        if isinstance(text, (bytes, bytearray)):
            hashcode.update(text)
        else:
            hashcode.update(text.encode("utf-8"))
        return hashcode.hexdigest()
    return None


def md5sum(filename):
    """
    md5sum - returns themd5 of the file
    """
    if os.path.isfile(filename):
        f = open(filename, mode='rb')
        d = hashlib.md5()
        while True:
            buf = f.read(4096)
            if not buf:
                break
            d.update(buf)
        f.close()
        res = d.hexdigest()
        return res
    else:
        return ""


def lock(filename, username):
    """
    lock - create a lock file
    """
    filelock = forceext(filename, "lock")
    os.makedirs(justpath(filelock), exist_ok=True)
    #get pid if username is not provided
    username = username or f"{os.getpid()}"
    with open(filelock, "w", encoding="utf-8") as f:
        f.write(f"{username},{datetime.datetime.now()}")


def unlock(filename):
    """
    unlock - remove the lock file
    """
    filelock = forceext(filename, "lock")
    if os.path.isfile(filelock):
        os.unlink(filelock)


def is_locked(filename, username, timeout=60):
    """
    is_locked - check if the file is locked
    """
    locked = False
    timeout = timeout or 60
    filelock = forceext(filename, "lock")
    if os.path.isfile(filelock):
        with open(filelock, "r", encoding="utf-8") as f:
            locker, locktime = f.read().split(",")
            if locker != username:
                locktime = datetime.datetime.strptime(locktime, "%Y-%m-%d %H:%M:%S.%f")
                if (datetime.datetime.now() - locktime).total_seconds() < timeout:
                    locked = True
                else:
                    # remove the lock file
                    os.unlink(filelock)
    return locked


def locked_by(filename):
    """
    locked_by - get the locker
    """
    filelock = forceext(filename, "lock")
    if os.path.isfile(filelock):
        with open(filelock, "r", encoding="utf-8") as f:
            locker, _ = f.read().split(",")
            return locker
    return None


def version_lower(current_version, version, strict=False):
    if strict and current_version == version:
        return False
    current_version = current_version.split(".")
    version = version.split(".")
    max_length = max(len(current_version), len(version))
    current_version += ['0'] * (max_length - len(current_version))
    version += ['0'] * (max_length - len(version))
    for i in range(max_length):
        if int(current_version[i]) < int(version[i]):
            return True
        elif int(current_version[i]) > int(version[i]):
            return False
    return True
