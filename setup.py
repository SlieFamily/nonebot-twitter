# _*_ coding:utf-8 _*_
from setuptools import setup, find_packages

with open("README.md", "r",encoding='UTF-8') as fh:
    long_description = fh.read()

setup(name='nonebot_plugin_twitter',
      version='1.0',   
      description='基于NoneBot2的Twitter推送插件，自带百度翻译接口',
      long_description=long_description,
      long_description_content_type="text/markdown",  
      author='鹿乃ちゃんの猫',  
      author_email='kano@hanayori.top',  
      url='https://github.com/kanomahoro/nonebot-twitter', 
      packages=find_packages(),  
      license="GPLv3",   
      classifiers=[
          "Programming Language :: Python :: 3", 
          "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
          "Operating System :: OS Independent"],
      python_requires='>=3.8',
      install_requires=[
        "nb-cli>=0.5.0",
        "nonebot-adapter-cqhttp>=2.0.0a15",
        "nonebot-plugin-apscheduler>=0.1.2",
        "selenium==2.48.0"
    ]
      )