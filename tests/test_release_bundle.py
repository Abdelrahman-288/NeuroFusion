import json
from pathlib import Path
import zipfile
import pytest
from neurofusion.release_bundle import build_bundle,verify_bundle,restore_bundle,safe_name

def test_roundtrip_and_existing_destination_protected(tmp_path):
    source=tmp_path/'source.txt';source.write_text('content');archive=tmp_path/'release.zip'
    build_bundle({'app/source.txt':source},archive);restore_bundle(archive,tmp_path/'restored')
    assert (tmp_path/'restored/app/source.txt').read_text()=='content'
    with pytest.raises(ValueError):restore_bundle(archive,tmp_path/'restored')
    with pytest.raises(ValueError):build_bundle({'app/source.txt':source},archive)

@pytest.mark.parametrize('name',['../escape','/absolute','C:/drive','a\\b','a/../b','con.txt','a./b','a//b'])
def test_unsafe_paths_rejected(name):
    with pytest.raises(ValueError):safe_name(name)

def test_corrupted_and_undeclared_payload_rejected(tmp_path):
    archive=tmp_path/'bad.zip'
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('bundle-manifest.json',json.dumps({'files':[{'path':'file','sha256':'0'*64,'bytes':4}]}));z.writestr('file',b'data')
    with pytest.raises(ValueError,match='checksum'):verify_bundle(archive)
    with zipfile.ZipFile(archive,'a') as z:z.writestr('extra','undeclared')
    with pytest.raises(ValueError,match='inventory'):verify_bundle(archive)
