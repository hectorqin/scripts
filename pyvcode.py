#!/usr/bin/env python
#-*- coding: utf-8 -*-
# python批量转码
import subprocess
import glob
import os
import re
import json
import getopt
import sys
import datetime
import time
import traceback

config = {
    "ffmpeg": "ffmpeg",
    "ffprobe": "ffprobe",
    "resolutions": {
        "1080p": {
            "vrate": 1500000,
            "arate": 196000,
            "scale": "-2:1080",
            "path": "%s/1080p/%s.1080p.mp4",
            "watermark": {
                "path": "/Users/aa/Desktop/htdocs/storage/resource/watermark/xuelele.1080p.png",
                "position": "96:54"
            }
        },
        "720p": {
            "vrate": 1000000,
            "arate": 128000,
            "scale": "-2:720",
            "path": "%s/720p/%s.720p.mp4",
            "watermark": {
                "path": "/Users/aa/Desktop/htdocs/storage/resource/watermark/xuelele.720p.png",
                "position": "64:36"
            }
        },
        "480p": {
            "vrate": 500000,
            "arate": 128000,
            "scale": "-2:480",
            "path": "%s/480p/%s.480p.mp4",
            "watermark": {
                "path": "/Users/aa/Desktop/htdocs/storage/resource/watermark/xuelele.480p.png",
                "position": "32:24"
            }
        },
        "origin": {
            "vrate": 2000000,
            "arate": 196000,
            "path": "%s/%s.mp4",
            "backup": "%s/origin/%s%s"
        }
    },
    "progressFile": "/tmp/pyvcode.progress",
    "progressDuration": 0,
    "threads": 8,
    "timeout": 3600,
    "loglevel": 'INFO,ERROR',
    # "partern": "/Users/aa/Desktop/htdocs/storage/test/*",
    "partern": os.getcwd() + "/*",
    "except": ".*.log",
    "watermark": False,
    "dryRun": True,
}


def runCmd(command, timeout=1800, onProgress=False):
    start = datetime.datetime.now()
    process = subprocess.Popen(
        command, shell=True, bufsize=10000, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    while process.poll() is None:
        time.sleep(0.1)
        now = datetime.datetime.now()
        if (now - start).seconds > timeout:
            try:
                process.terminate()
            except Exception, e:
                return None
            return None
        if callable(onProgress):
            onProgress(process)
    output, error = process.communicate()
    if process.stdin:
        process.stdin.close()
    if process.stdout:
        process.stdout.close()
    if process.stderr:
        process.stderr.close()
    try:
        process.kill()
    except OSError:
        pass
    if error:
        log(error, "ERROR")
    return output


def log(msg, level='INFO'):
    if level in config["loglevel"]:
        print "[ %s ] %s" % (level, msg)


def showProgress(progress, prefix='', suffix=''):
    width = 20
    sys.stdout.write(' ' * (width + len(prefix) + len(suffix) + 2) + '\r')
    sys.stdout.flush()
    sys.stdout.write(str(prefix) + str(progress) + "%")
    p_right = int(progress * width / 100)
    p_left = width - p_right
    sys.stdout.write('[' + '#' * p_right + '-' *
                     p_left + ']' + str(suffix) + '\r')
    if progress == 100:
        sys.stdout.write('\n')
    sys.stdout.flush()


def getPositionInList(list, value, rtype=0):
    if value in list:
        return list.index(value)
    list.append(value)
    list.sort()
    k = list.index(value)
    if rtype == 0:  # 较小
        return k - 1 if k > 0 else 0
    elif rtype == 1:  # 较大
        return k + 1
    else:  # 较近
        if k == 0:
            return k + 1
        elif k == len(list) - 1:
            return k - 1
        else:
            return k - 1 if list[k + 1] - value >= value - list[k - 1] else k + 1


def isExcept(path):
    if len(config["except"]):
        return re.search(config["except"], path)


def extractRatio(info, name):
    ratio = info.get(name, '').split(":")
    ratio = filter((lambda x: int(x) > 0), ratio)
    if len(ratio) == 2:
        return map((lambda x: int(x)), ratio)
    return None


def getDimension(info):
    width = info.get('width')
    height = info.get('height')
    if not width or not height:
        return width, height
    sampleRatio = extractRatio(info, 'sample_aspect_ratio')
    displayRatio = extractRatio(info, 'display_aspect_ratio')
    log("sampleRatio: " + str(sampleRatio), "DEBUG")
    log("displayRatio: " + str(displayRatio), "DEBUG")
    if sampleRatio and displayRatio:
        if sampleRatio[0] != 1 and sampleRatio[1] != 1:
            width = round(
                width * (float(sampleRatio[0]) / float(sampleRatio[1])))
            height = round(
                width * (float(displayRatio[1]) / float(displayRatio[0])))
    return width, height


def getMediaSimpleInfo(path):
    if not os.path.isfile(path):
        return False
    isMedia = runCmd("file %s | grep -i media" % path)
    if not len(isMedia):
        return False
    mediaInfo = runCmd(
        "%s -v quiet  -show_streams -print_format json %s" % (config["ffprobe"], path))
    formatInfo = runCmd("%s -v quiet -print_format json -show_format % s" %
                        (config["ffprobe"], path))
    formatInfo = json.loads(formatInfo)
    mediaInfo = json.loads(mediaInfo)

    log("formatInfo: " + json.dumps(formatInfo, indent=4, sort_keys=True), "DEBUG")
    log("mediaInfo: " + json.dumps(mediaInfo, indent=4, sort_keys=True), "DEBUG")
    simpleInfo = {
        "path": path,
        "format": formatInfo["format"].get('format_name', ''),
        "size": os.path.getsize(path),
        "major_brand": formatInfo["format"].get('tags', {}).get('major_brand', ''),
        "duration": formatInfo["format"].get('duration'),
    }
    for stream in mediaInfo["streams"]:
        if stream["codec_type"] == "video":
            simpleInfo['sample_aspect_ratio'] = stream.get(
                'sample_aspect_ratio', None)
            simpleInfo['display_aspect_ratio'] = stream.get(
                'display_aspect_ratio', None)
            simpleInfo['width'] = stream.get('width', None)
            simpleInfo['height'] = stream.get('height', None)
            if not simpleInfo['width'] or not simpleInfo['height']:
                continue
            simpleInfo['width'], simpleInfo[
                'height'] = getDimension(simpleInfo)
            simpleInfo['video_bit_rate'] = stream.get('bit_rate', 0)
            simpleInfo['video_codec_name'] = stream['codec_name']
            simpleInfo['is_avc'] = stream['is_avc']
            simpleInfo['aspect'] = round(
                float(simpleInfo['width']) / simpleInfo['height'], 4)
        elif stream["codec_type"] == "audio":
            simpleInfo['audio_codec_name'] = stream['codec_name']
            simpleInfo['audio_bit_rate'] = stream.get('bit_rate', 0)
    if not simpleInfo['width'] or not simpleInfo['height']:
        return False
    resolutionList = ["origin", "480p", "720p", "1080p"]
    widthArr = [640, 1280, 1920, 2560, 4096]
    heightArr = [480, 720, 1080, 1440, 2160]
    # position = max(getPositionInList(widthArr, simpleInfo['width']), getPositionInList(heightArr, simpleInfo['height']))
    # 以纵线像素为准
    position = getPositionInList(heightArr, simpleInfo['height'])
    simpleInfo['resolution'] = resolutionList[position + 1]
    simpleInfo['avaliableResolution'] = resolutionList[0:(position + 2)]
    simpleInfo['avaliableResolution'] = parseAvalibleResolution(
        path, simpleInfo['avaliableResolution'])
    log("simpleInfo: " + json.dumps(simpleInfo, indent=4, sort_keys=True), "DEBUG")
    return simpleInfo


def parseAvalibleResolution(path, avaliableResolution):
    for resolution in avaliableResolution:
        if resolution == "origin":
            continue
        r_path = getResolutionFilePath(path, resolution)
        log("==>检查%s分辨率视频文件%s" % (resolution, r_path))
        if os.path.isfile(r_path):
            log("%s分辨率视频文件%s已存在" % (resolution, r_path))
            avaliableResolution.remove(resolution)
    return avaliableResolution


def getResolutionFilePath(path, resolution, ptype="path"):
    dir_name = os.path.dirname(path)
    file_name_ext = os.path.splitext(os.path.basename(path))
    if ptype == "path":
        return config["resolutions"][resolution][ptype] % (dir_name, file_name_ext[0])
    else:
        return config["resolutions"][resolution][ptype] % (dir_name, file_name_ext[0], file_name_ext[1])


def parseResolution(mediaInfo, resolution):
    resolutionConfig = config["resolutions"][resolution]
    if mediaInfo["video_bit_rate"] and int(mediaInfo["video_bit_rate"]) > resolutionConfig["vrate"]:
        vrate = resolutionConfig["vrate"]
    else:
        vrate = None
    if mediaInfo["audio_bit_rate"] and int(mediaInfo["audio_bit_rate"]) > resolutionConfig["arate"]:
        arate = resolutionConfig["arate"]
    else:
        arate = None

    outFile = getResolutionFilePath(mediaInfo["path"], resolution)
    return resolutionConfig.get("scale", None), vrate, arate, checkDir(outFile)


def checkDir(path):
    _dir = os.path.dirname(path)
    if not os.path.isdir(_dir) and not config["dryRun"]:
        os.makedirs(_dir)
    return path


def getTranscodeCmd(mediaInfo):
    if config["watermark"]:
        watermark = config["resolutions"][mediaInfo["resolution"]]["watermark"]
        filterArgs = "'-filter_complex' 'movie=%s [watermark]; [0][watermark] overlay=%s [out];[out]split=%s'" % (watermark[
            "path"], watermark[
            "position"], '%s')
    else:
        filterArgs = "'-filter_complex' '[0]split=%s'"
    commonArgs = "'-async' '1' '-metadata' 'description=Coded by New Xuelele Transcoder v1.0' '-refs' '6' '-coder' '1' '-sc_threshold' '40' '-flags' '+loop' '-me_range' '16' '-subq' '7' '-i_qfactor' '0.71' '-qcomp' '0.6' '-qdiff' '4' '-trellis' '1'"
    splitFilter = ""
    resizeFilter = ""
    outputList = []
    backupCmd = ""
    inputFile = mediaInfo["path"]
    for resolution in mediaInfo["avaliableResolution"]:
        if resolution == "origin":
            inputFile = checkDir(getResolutionFilePath(
                mediaInfo["path"], "origin", "backup"))
            backupCmd = "'cp' '%s' '%s' && " % (
                mediaInfo["path"], inputFile)
        scale, vrate, arate, outFile = parseResolution(mediaInfo, resolution)
        if vrate:
            vrate = "'-b:v' '%s'" % vrate
        else:
            vrate = ""
        if arate:
            arate = "'-b:a' '%s'" % arate
        else:
            arate = ""

        filterIn = "[in%d]" % (mediaInfo[
            "avaliableResolution"].index(resolution) + 1)
        filterOut = "[out%d]" % (mediaInfo[
                    "avaliableResolution"].index(resolution) + 1)
        if scale:
            splitFilter += filterIn
            resizeFilter += "%sscale=%s%s;" % (filterIn, scale, filterOut)
        else:
            splitFilter += filterOut
        output = "'-map' '%s' '-map' '0:a' '-vcodec' 'libx264' '-acodec' 'aac' %s %s %s '%s' " % (
            filterOut, vrate, arate, commonArgs, outFile)
        outputList.append(output)
    splitFilter = str(len(outputList)) + splitFilter + ";"
    filterArgs = filterArgs % (splitFilter + resizeFilter).rstrip(";")
    transcodeCmd = "%s '%s' '-v' 'warning' '-y' '-hide_banner' '-progress' 'file:%s' '-i' '%s' '-threads' '%d' %s %s" % (
        backupCmd, config["ffmpeg"], config["progressFile"], inputFile, config["threads"], filterArgs, " ".join(outputList))
    return transcodeCmd


def onTranscodeProgress(process=None):
    time.sleep(0.9)
    if not os.path.isfile(config["progressFile"]):
        return
    with open(config["progressFile"], 'r') as f:
        lines = f.read()
        try:
            progress = re.compile(ur'progress\=([\w]+)').findall(lines)
            nowtime = re.compile(ur'out_time_ms\=([\d]+)').findall(lines)
            if progress:
                progress = progress[-1]
            if nowtime:
                nowtime = nowtime[-1]
            if progress == "continue":
                i = int(int(nowtime) / int(10000 * config["progressDuration"]))
                showProgress(i, "[ INFO ] Progress: ")
            elif progress == "end":
                config["progressEnd"] = datetime.datetime.now()
                showProgress(100, "[ INFO ] Progress: ", " [ Runtime: %ds]" % (
                    config["progressEnd"] - config["progressStart"]).seconds)
                os.remove(config["progressFile"])
        except Exception, e:
            traceback.print_exc()


def usage():
    print '''
Transcode video files that match the partern of configuration, version is 1.0.
Usage:
    pyvcode [--help|--dryrun|--run|--watermark|--partern=RegEx|--except=RegEx|--loglevel=string]
Options:
    --help: show help information.
    --watermark: put the watermark on video files
    --dryrun: run this script once without transcode video files, default is dryrun
    --run: run this script once and transcode video files.
    --partern=RegEx: change the partern RegEx of match files
    --except=RegEx: change the except RegEx of match files
    --loglevel=string: set the logging level
'''


def main():
    for path in glob.glob(config["partern"]):
        log("检查文件" + path)
        if isExcept(path):
            log("排除文件" + path)
        mediaInfo = getMediaSimpleInfo(path)
        if not mediaInfo:
            continue
        log("视频文件信息" + json.dumps(mediaInfo, indent=4, sort_keys=True))
        if len(mediaInfo["avaliableResolution"]):
            transcodeCmd = getTranscodeCmd(mediaInfo)
            log("转码命令  " + transcodeCmd)
            if not config["dryRun"]:
                log("转码中...")
                config["progressDuration"] = float(mediaInfo["duration"])
                config["progressStart"] = datetime.datetime.now()
                runCmd(transcodeCmd, config["timeout"], onTranscodeProgress)


if __name__ == '__main__':
    opts, args = getopt.getopt(
        sys.argv[1:], '', ["help", "dryrun", "run", "watermark", "partern=", "except=", "loglevel="])
    for op, value in opts:
        if op == "--help":
            usage()
            sys.exit()
        elif op == "--dryrun":
            config["dryRun"] = True
        elif op == "--run":
            config["dryRun"] = False
        elif op == "--watermark":
            config["watermark"] = True
        elif op == "--partern":
            config["partern"] = value
        elif op == "--except":
            config["except"] = value
        elif op == "--loglevel":
            config["loglevel"] = value
    log("当前配置" + str(config))
    main()
