# ==================================================================================================================== #
# ----------------------------------------------------- 配置区 -------------------------------------------------------- #
# ==================================================================================================================== #
"""要复制的Resource文件"""
PREFIX = '.\\application\\resources'
SOURCES = (
    "tools\\ffmpeg-4.0-win64-static\\bin\\ffmpeg.exe",
    "logo\\police.ico",
    "tools\\VLC",
    # "tools\\mediaServer",
    # "tools\\PDF\\wkhtmltopdf.exe",
)
# -------------------------------------------------------------------------------------------------------------------- #


import os
import shutil
import logging

LOG = logging.getLogger('copy_resources')
LOG.setLevel(logging.DEBUG)
FORMAT = logging.Formatter('%(asctime)-15s %(module)s.%(funcName)s[%(lineno)d] %(levelname)s %(message)s')
sh = logging.StreamHandler()
sh.setFormatter(FORMAT)
sh.setLevel(logging.DEBUG)
fh = logging.FileHandler('./copy_resources.log', mode='a', encoding='utf-8')
fh.setFormatter(FORMAT)
fh.setLevel(logging.DEBUG)
LOG.addHandler(sh)
LOG.addHandler(fh)


def copyFiles(sourceDir, targetDir):
    """
        把某一目录下的所有文件复制到指定目录中
    """
    if sourceDir.find(".svn") > 0:
        return
    for file in os.listdir(sourceDir):
        sourceFile = os.path.join(sourceDir, file)
        targetFile = os.path.join(targetDir, file)
        if os.path.isfile(sourceFile):
            if not os.path.exists(targetDir):
                os.makedirs(targetDir)
            if not os.path.exists(targetFile) or (
                    os.path.exists(targetFile) and (os.path.getsize(targetFile) != os.path.getsize(sourceFile))):
                open(targetFile, "wb").write(open(sourceFile, "rb").read())
        if os.path.isdir(sourceFile):
            First_Directory = False
            copyFiles(sourceFile, targetFile)


def copy_resources():
    for s in SOURCES:
        full_path = os.path.join(PREFIX, s)
        base_name = os.path.basename(full_path)
        if os.path.exists(base_name):
            LOG.debug("{}已存在，无需拷贝.".format(base_name))
            continue
        if os.path.isfile(full_path):
            try:
                shutil.copy(full_path, '.')
                LOG.info("拷贝文件{}".format(base_name))
            except Exception as e:
                LOG.error(e)
        else:
            try:
                copyFiles(full_path, '.')
                LOG.info("拷贝文件夹{}".format(base_name))
            except Exception as e:
                LOG.error(e)
    LOG.info('拷贝执行完毕.\n')


def deal_with_statics():
    ret = False
    try:
        copy_resources()
    except Exception as e:
        LOG.error("拷贝出错：{}".format(e))
        return ret
    ret = True
    return ret


def main():
    confirm = input("~~~~~~~~~~~~\nFBI Warning \n~~~~~~~~~~~~\n如果本地Resource或Model有新增内容，请手动上传到Nexus后再执行脚本，否则文件可能会丢失！"
                    "是否继续执行(Y/N)").lower()
    if confirm == 'y':
        pass
    else:
        return
    # 处理静态资源
    deal_with_statics()

    LOG.info("程序执行完毕. 请不要删除zip文件，留作对比MD5！")


if __name__ == '__main__':
    main()
