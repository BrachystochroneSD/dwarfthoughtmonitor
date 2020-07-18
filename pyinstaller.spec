# -*- mode: python -*-
import shutil, os

block_cipher = None

a = Analysis(['dtm/__main__.py'],
             pathex=['D:\\workspace\\Dwarf Thought Monitor\\DwarfThoughtMonitor'],
             binaries=None,
             datas=None,
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             win_no_prefer_redirects=None,
             win_private_assemblies=None,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='DwarfThoughtMonitor',
          debug=False,
          strip=None,
          upx=True,
          console=False,
          icon='data\\favicon.ico',
          )

os.makedirs('dist/data')
shutil.copyfile('data/favicon.ico', 'dist/data/favicon.ico')
shutil.copyfile('filters.txt', 'dist/filters.txt')
shutil.copyfile('data/filters.dat', 'dist/data/filters.dat')
shutil.copyfile('README.md', 'dist/readme.txt')
