"""
# Terminal status control.
"""
import io
from fault.terminal import matrix

class Control(object):
	"""
	# Status control.
	"""

	def __init__(self, device, screen, context):
		self.device = device
		self.screen = screen
		self.context = context

		self.Normal = context.terminal_type.normal_render_parameters
		self.Key = self.Value = self.Space = self.Field = self.Normal

		self._io = io.FileIO(device.fileno(), closefd=False, mode='w')
		self._prefix = ""

	def initialize(self, order):
		self._prefix = None
		self._suffix = None
		self.field_order = order
		self.field_values = {}
		self.field_value_override = {}

	def prefix(self, *words):
		self._prefix = words

	def suffix(self, *words):
		self._suffix = words

	def alignment(self, pad=" " ):
		for x in range(len(self.field_order)-1):
			yield pad

		yield ""

	def render(self):
		if self._prefix:
			yield from self._prefix
			yield self.Space.form(" ")

		for k, fpad in zip(self.field_order, self.alignment()):
			v = self.field_values.get(k, None)
			if v is None:
				continue


			yield self.Key.form(k + ":")
			yield self.Space.form(" ")

			rp = self.field_value_override.get(k, self.Value)
			yield rp.form(str(v))

			yield self.Space.form(fpad)

		if self._suffix:
			yield from self._suffix

	def update(self, fields):
		self.field_values.update(fields)

		buf = self.screen.exit_scrolling_region() + self.context.seek_first()

		l = self.context.Phrase.from_words(*self.render())
		i = self.context.print([l], [l.cellcount()])

		buf += b''.join(i)
		buf += self.screen.enter_scrolling_region()

		self._io.write(buf)

	def flush(self, output):
		l = self.context.Phrase.from_words(*self.render())
		i = self.context.print([l], [l.cellcount()])
		output.write(b''.join(i))
		output.write(b'\n')
		output.flush()

def setup(lines:int, width=None, atrestore=b'', type='prepared',
		destruct=True, Context=matrix.Context,
	):
	"""
	# Initialize the terminal for use with a scrolling region.
	# Constructs a device using &control.setup and a &matrix.Context
	# pointing to the status region.
	"""
	import os
	from fault.terminal import control
	screen = matrix.Screen()

	device, pre, res = control.setup(type,
		atrestore=screen.close_scrolling_region()+atrestore,
		destruct=destruct,
	)

	hv = device.get_window_dimensions()
	screen.context_set_dimensions(hv)

	v = hv[1] - lines
	if width is not None:
		h = min(hv[0], width)
	else:
		h = hv[0]

	init = screen.open_scrolling_region(0, v-1)
	#init += screen.terminal_type.decset((om,))
	#init += screen.seek_bottom()
	#init += screen.store_cursor_location()

	ctx = Context(screen.terminal_type)
	ctx.context_set_position((0, v))
	ctx.context_set_dimensions((h, lines))

	pre()
	atexit.register(res)
	os.write(device.fileno(), init)
	return Control(device, screen, ctx)

if __name__ == '__main__':
	st_ctl = setup()
	st_ctl.initialize(['field-1', 'field-2'])
	st_ctl.update({'field-1': 0, 'field-2': 'test'})
	print('test-1')
	print('test-2')
	import time
	time.sleep(3)
