#!/usr/bin/env python3
"""Staged shared iPhone cache QA; fictional loopback data, no paid providers."""
from pathlib import Path
import argparse
import subprocess,time,sys
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--simulator',required=True)
parser.add_argument('--derived-data',default='/tmp/SharedRoomCacheBuild')
parser.add_argument('--results',required=True)
args=parser.parse_args()
base=Path('/tmp/voice-note-cache-qa')
out=Path(args.results);out.mkdir(parents=True,exist_ok=False)
service=None
counter=0
def helper(mode,test=None):
    subprocess.run([sys.executable,'scripts/note_cache_fixture.py',mode]+(['--stage',test] if test else []),cwd=root,check=True)
def stop():
    global service
    if service:
        import os,signal
        os.killpg(service.pid,signal.SIGTERM);service.wait();service=None

def start(mode,test=None):
    global service
    service=subprocess.Popen([sys.executable,'scripts/note_cache_fixture.py',mode]+(['--stage',test] if test else []),cwd=root,start_new_session=True,stdout=open(out/(mode+'.log'),'a'),stderr=subprocess.STDOUT)
    deadline=time.monotonic()+10
    while not (base/'config.json').exists():
        if service.poll() is not None or time.monotonic()>deadline:raise RuntimeError('fixture failed')
        time.sleep(.1)
def fresh():
    stop()
    if base.exists():base.rename('/tmp/voice-note-cache-qa-evidence-'+str(time.time_ns()))
    start('populate','testSharedCachePopulate')
    test('testSharedCachePopulate')
def test(name):
    global counter
    counter+=1; label=f'{counter}-{name}'
    with open(out/(label+'.log'),'w') as log:
        subprocess.run(['xcodebuild','-project','VoiceCompanion.xcodeproj','-scheme','Phone','-destination',f'platform=iOS Simulator,id={args.simulator}','-derivedDataPath',args.derived_data,'-resultBundlePath',str(out/(label+'.xcresult')),'-only-testing:PhoneUITests/SharedRoomCacheUITests/'+name,'test','CODE_SIGNING_ALLOWED=NO'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
    print('PASS',label,flush=True)
try:
    subprocess.run(['xcodegen','generate'],cwd=root,check=True)
    fresh();stop();helper('stage','testSharedCacheOffline');test('testSharedCacheOffline')
    helper('update','testSharedCacheUpdate');start('read');test('testSharedCacheUpdate')
    helper('source-revision','testSharedCacheStale');test('testSharedCacheStale')
    fresh();stop();helper('source-delete','testSharedCacheRemoteDelete');start('read');test('testSharedCacheRemoteDelete')
    fresh();helper('stage','testSharedCacheLocalDelete');test('testSharedCacheLocalDelete')
finally:stop()
