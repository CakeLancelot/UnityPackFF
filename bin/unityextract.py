#!/usr/bin/env python3
import os
import pickle
import sys
import traceback
import unitypack
from argparse import ArgumentParser
from io import BytesIO
from unitypack.asset import Asset
from unitypack.export import OBJMesh
from unitypack.utils import extract_audioclip_samples


class UnityExtract:
	FORMAT_ARGS = {
		"audio": "AudioClip",
		"fonts": "Font",
		"images": "Texture2D",
		"models": "Mesh",
		"shaders": "Shader",
		"text": "TextAsset",
		"video": "MovieTexture",
	}

	def __init__(self, args):
		self.parse_args(args)

	def parse_args(self, args):
		p = ArgumentParser()
		p.add_argument("files", nargs="+")
		p.add_argument("--all", action="store_true", help="Extract all supported types")
		for arg, clsname in self.FORMAT_ARGS.items():
			p.add_argument("--" + arg, action="store_true", help="Extract %s" % (clsname))
		p.add_argument("-o", "--outdir", nargs="?", default="", help="Output directory")
		p.add_argument("--as-asset", action="store_true", help="Force open files as Asset format")
		p.add_argument("--filter", nargs="*", help="Filter extraction for a specific name")
		p.add_argument("-n", "--dry-run", action="store_true", help="Skip writing files")
		self.args = p.parse_args(args)

		self.handle_formats = []
		for a, classname in self.FORMAT_ARGS.items():
			if self.args.all or getattr(self.args, a):
				self.handle_formats.append(classname)

	def run(self):
		for file in self.args.files:
			if self.args.as_asset or file.endswith(".assets"):
				with open(file, "rb") as f:
					try:
						asset = Asset.from_file(f)
						self.handle_asset(asset)
					except:
						traceback.print_exc()
				continue

			with open(file, "rb") as f:
				bundle = unitypack.load(f)

				for asset in bundle.assets:
					self.handle_asset(asset)

		return 0

	def get_output_path(self, filename):
		basedir = os.path.abspath(self.args.outdir)
		path = os.path.join(basedir, filename)
		dirs = os.path.dirname(path)
		if not os.path.exists(dirs):
			os.makedirs(dirs)
		return path

	def write_to_file(self, filename, contents, mode="w"):
		path = self.get_output_path(filename)

		if self.args.dry_run:
			print("Would write %i bytes to %r" % (len(contents), path))
			return

		with open(path, mode) as f:
			written = f.write(contents)

		print("Wrote %i bytes to %r" % (written, path))
		
	def _handle_asset(self, asset, id, obj):
		if obj.type not in self.handle_formats:
			return

		def matches(name, filters):
			for f in filters:
				if f.lower() in name:
					return True
			return False

		d = obj.read()
		if self.args.filter and not matches(d.name.lower(), self.args.filter):
			return

		if obj.type == "AudioClip":
			if asset.format == 6 or asset.format == 7:
				self.write_to_file(d.name + ".ogg", d.audio_data, mode="wb")
			else:
				samples = extract_audioclip_samples(d)
				for filename, sample in samples.items():
					self.write_to_file(filename, sample, mode="wb")

		elif obj.type == "MovieTexture":
			filename = d.name + ".ogv"
			self.write_to_file(filename, d.movie_data, mode="wb")

		elif obj.type == "Shader":
			self.write_to_file(d.name + ".cg", d.script)

		elif obj.type == "Mesh":
			try:
				mesh_data = OBJMesh(d).export()
				self.write_to_file(d.name + ".obj", mesh_data, mode="w")
			except NotImplementedError as e:
				print("WARNING: Could not extract %r (%s)" % (d, e))
				#mesh_data = pickle.dumps(d._obj)
				#self.write_to_file(d.name + ".Mesh.pickle", mesh_data, mode="wb")

		elif obj.type == "Font":
			self.write_to_file(d.name + ".ttf", d.data, mode="wb")

		elif obj.type == "TextAsset":
			if isinstance(d.script, bytes):
				filename, mode = d.name + ".bin", "wb"
			else:
				filename, mode = d.name + ".txt", "w"
			self.write_to_file(filename, d.script, mode=mode)

		elif obj.type == "Texture2D":
			filename = d.name + ".png"
#			if filename.lower().endswith('.dds.png'):
#				filename = filename[:len('.dds.png')] + '.png'

			try:
				from PIL import ImageOps
			except ImportError:
				print("WARNING: Pillow not available. Skipping %r." % (filename))
				return
			try:
				image = d.image
			except NotImplementedError:
				print("WARNING: Texture format not implemented. Skipping %r." % (filename))
				return

			if image is None:
				print("WARNING: %s is an empty image" % (filename))
				return

			print("Decoding %r" % (d))
			# Texture2D objects are flipped
			img = ImageOps.flip(image)
			# PIL has no method to write to a string :/
			output = BytesIO()
			img.save(output, format="png")
			self.write_to_file(filename, output.getvalue(), mode="wb")

	def handle_asset(self, asset):
		for id, obj in asset.objects.items():
			try:
				self._handle_asset(asset, id, obj)
			except Exception as e:
				if isinstance(e, KeyboardInterrupt):
				    break
				print('ERROR WHILE DECODING {}:'.format(id))
				traceback.print_exc()

def main():
	app = UnityExtract(sys.argv[1:])
	exit(app.run())


if __name__ == "__main__":
	main()
