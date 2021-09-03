# -*- mode: python -*-

block_cipher = None

env_py_path = "D:\\venv\\base"

added_files = [
                ('.\\MODELS', '.\\MODELS'),
                ('.\\model', '.\\model'),
                ('.\\AU_predictors', '.\\AU_predictors'),
                ('.\\classifiers', '.\\classifiers'),
                ('.\\conf\\*.yaml', 'conf'),
                ('.\\application\\resources\\icons\\', '.\\application\\resources\\icons\\'),
                ('.\\application\\resources\\report_files\\templates\\*.html', '.\\application\\resources\\report_files\\templates\\'),
                ('.\\application\\resources\\tools\\VLC\\hrtfs', 'hrtfs'),
                ('.\\application\\resources\\tools\\VLC\\locale', 'locale'),
                ('.\\application\\resources\\tools\\VLC\\lua', 'lua'),
                ('.\\application\\resources\\tools\\VLC\\plugins', 'plugins'),
                ('.\\application\\resources\\tools\\VLC\\skins', 'skins'),
                ('.\\application\\resources\\tools\\VLC\\*.*', '.'),
                ('.\\application\\resources\\tools\\ffmpeg-4.0-win64-static\\bin\\ffmpeg.exe', '.'),
                ('.\\application\\resources\\tools\\PDF\\wkhtmltopdf.exe', '.'),
                ('C:\\Users\\Administrator\\Envs\\eda_qdjc_env\\Lib\\site-packages\\resampy\\data', 'resampy\\data'),
                ('C:\\Users\\Administrator\\Envs\\eda_qdjc_env\\Lib\\site-packages\\sklearn\\tree\\_utils.cp36-win_amd64.pyd', 'sklearn\\tree'),
                ('C:\\Users\\Administrator\\Envs\\eda_qdjc_env\\Lib\\site-packages\\docx\\templates\\default.docx', '.\\docx\\templates\\'),
              ]

hidden_modules = ['scipy.integrate', 'scipy._lib.messagestream',
                'sklearn.neighbors.typedefs', 'sklearn.neighbors.quad_tree', 'sklearn.tree',
                'tensorflow.contrib', 'application.controller.algorithm.openface',]

binaries_dll = [
                ('C:\\Users\\Administrator\\Envs\\eda_qdjc_env\\Lib\\site-packages\\cv2\\opencv_ffmpeg340_64.dll', '.'),
                ('C:\\Users\\Administrator\\Envs\\eda_qdjc_env\\Lib\\site-packages\\scipy\\extra-dll\\*','.'),
                ('.\\application\\controller\\algorithm\\OpenFace\\core\\*.pyd', '.\\application\\controller\\algorithm\\OpenFace\\core\\'),
                ('.\\application\\controller\\algorithm\\OpenFace\\core\\*.dll', '.\\application\\controller\\algorithm\\OpenFace\\core\\'),
                ('.\\application\\resources\\tools\\temperature\\ftd2xx.dll', '.'),
                ]



a = Analysis(['AI_main.py'],
             pathex=['E:\\work\\main\\EDA_MAIN_SERVER\\src'],
             binaries=binaries_dll,
             datas=added_files,
             hiddenimports=hidden_modules,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='AI_main',
          debug=False,
          strip=False,
          upx=True,
          console=False,
          icon='E:\\work\\main\\EDA_MAIN_SERVER\\src\\application\\resources\\logo\\police.ico'
          )

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='main')
