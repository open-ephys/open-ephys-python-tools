from setuptools import setup

setup(name='open-ephys-python-tools',
      version='0.0.1',
      description='Software tools for interfacing with the Open Ephys GUI',
      url='http://github.com/open-ephys/open-ephys-python-tools',
      author='Josh Siegle',
      author_email='josh@open-ephys.org',
      license='MIT',
      packages=['open_ephys.analysis',
                'open_ephys.analysis.formats',
                'open_ephys.analysis.formats.helpers',
                'open_ephys.control',
                'open_ephys.streaming'],
      classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"],
        install_requires=[
              'numpy',
              'pandas', 
              'h5py',
              'zmq'])