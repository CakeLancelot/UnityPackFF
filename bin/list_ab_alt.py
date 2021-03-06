#!/usr/bin/env python3

import sys
from unitypack.asset import Asset

def main(f):
	asset = Asset.from_file(f)

	container = asset.objects[1].read()['m_Container']
	for path, mtdt in container:
		t = mtdt['asset'].object.type
		print('{}\t{}\t{}\t{}'.format(mtdt['asset'].path_id, mtdt['asset'].file_id, t, path))

if __name__ == '__main__':
	with open(sys.argv[1], 'rb') as f:
		main(f)
