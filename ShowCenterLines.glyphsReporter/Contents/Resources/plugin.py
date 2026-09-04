# encoding: utf-8

###########################################################################################################
#
#
# Reporter Plugin
#
# Read the docs:
# https://github.com/schriftgestalt/GlyphsSDK/tree/master/Python%20Templates/Reporter
#
#
###########################################################################################################

import objc
import traceback
from math import isinf, isnan, radians, tan
from Foundation import NSMidX, NSMidY, NSAffineTransform, NSMakePoint, NSPoint, NSColor, NSBezierPath
import GlyphsApp
from GlyphsApp import Glyphs
from GlyphsApp.plugins import ReporterPlugin
if Glyphs.versionNumber >= 3:
	from GlyphsApp import GSGuide
else:
	from GlyphsApp import GSGuideLine as GSGuide

# Hint types used for corner, cap, brush and segment components. Not every
# Glyphs version exports all of them, hence the defensive lookup:
CORNERISH_HINT_TYPES = tuple(
	getattr(GlyphsApp, constantName)
	for constantName in ("CORNER", "CAP", "BRUSH", "SEGMENT")
	if hasattr(GlyphsApp, constantName)
)

# Glyph name prefixes of corner-component-like glyphs:
CORNERISH_NAME_PREFIXES = ("_corner.", "_cap.", "_brush.", "_segment.")


def isFiniteNumber(value):
	"""
	True only for real numbers we can safely calculate with. Guards against the
	None, NaN and infinity that Glyphs hands out for unmeasurable selections.
	"""
	try:
		return not (isinf(value) or isnan(value))
	except (TypeError, ValueError):
		return False


def transform(shiftX=0.0, shiftY=0.0, rotate=0.0, skew=0.0, scale=1.0):
	"""
	Returns an NSAffineTransform object for transforming layers.
	Apply an NSAffineTransform t object like this:
		Layer.transform_checkForSelection_doComponents_(t,False,True)
	Access its transformation matrix like this:
		tMatrix = t.transformStruct() # returns the 6-float tuple
	Apply the matrix tuple like this:
		Layer.applyTransform(tMatrix)
		Component.applyTransform(tMatrix)
		Path.applyTransform(tMatrix)
	Chain multiple NSAffineTransform objects t1, t2 like this:
		t1.appendTransform_(t2)
	"""
	myTransform = NSAffineTransform.transform()
	if rotate:
		myTransform.rotateByDegrees_(rotate)
	if scale != 1.0:
		myTransform.scaleBy_(scale)
	if not (shiftX == 0.0 and shiftY == 0.0):
		myTransform.translateXBy_yBy_(shiftX, shiftY)
	if skew:
		myTransform.shearXBy_(tan(radians(skew)))
	return myTransform


def isCornerComponent(thisObject):
	"""
	True if thisObject is a corner, cap, brush or segment component, or the
	pseudo path/node Glyphs 4 exposes for one. Those carry no meaningful
	coordinates for a center crosshair, and asking them for bounds can throw.
	Anything we cannot inspect is reported as corner-component-like, so the
	caller skips it rather than choking on it.
	"""
	if thisObject is None:
		return True
	try:
		# Glyphs 2 and 3 keep corner components in layer.hints:
		if "Hint" in thisObject.__class__.__name__:
			return True

		# Glyphs 4 may expose them as shapes with a corner-ish hint type.
		# Node types (LINE, CURVE, OFFCURVE) never collide with these values:
		if CORNERISH_HINT_TYPES:
			hintType = getattr(thisObject, "type", None)
			if hintType is not None and hintType in CORNERISH_HINT_TYPES:
				return True

		# Fall back to the glyph name, which is the same in every Glyphs version:
		for attributeName in ("name", "componentName"):
			name = getattr(thisObject, attributeName, None)
			if isinstance(name, str) and name.startswith(CORNERISH_NAME_PREFIXES):
				return True
		referencedName = getattr(getattr(thisObject, "component", None), "name", None)
		if isinstance(referencedName, str) and referencedName.startswith(CORNERISH_NAME_PREFIXES):
			return True
	except Exception:
		# Something in the selection we cannot even look at: skip it.
		return True
	return False


class ShowCenterLines(ReporterPlugin):

	@objc.python_method
	def settings(self):
		self.menuName = Glyphs.localize({
			'en': 'Center Lines',
			'de': 'Mittellinien',
			'es': 'lineas centrales',
			'fr': 'lignes centrales',
		})
		self.reportedProblems = set()

	@objc.python_method
	def logOnce(self, key, message):
		"""
		Logs message to the Macro Window once per key and Glyphs session.
		Reporters redraw many times per second, so an unguarded log (or an
		unguarded exception) turns a single problem into a flood.
		"""
		if not hasattr(self, "reportedProblems"):
			self.reportedProblems = set()
		if key in self.reportedProblems:
			return
		self.reportedProblems.add(key)
		try:
			self.logToConsole(message)
		except Exception:
			print(message)

	@objc.python_method
	def italicize(self, thisPoint, italicAngle=0.0, pivotalY=0.0):
		"""
		Returns the italicized position of an NSPoint 'thisPoint'
		for a given angle 'italicAngle' and the pivotal height 'pivotalY',
		around which the italic slanting is executed, usually half x-height.
		Usage: myPoint = italicize(myPoint, 10, xHeight * 0.5)
		"""
		x = thisPoint.x
		yOffset = thisPoint.y - pivotalY  # calculate vertical offset
		italicAngle = radians(italicAngle)  # convert to radians
		tangens = tan(italicAngle)  # math.tan needs radians
		horizontalDeviance = tangens * yOffset  # vertical distance from pivotal point
		x += horizontalDeviance  # x of point that is yOffset from pivotal point
		return NSPoint(x, thisPoint.y)

	@objc.python_method
	def italicAngleOfLayer(self, layer):
		"""
		Returns the italic angle of the layer’s master, 0.0 if there is none.
		Layers without a master (e.g. in Glyphs 4 during certain edits) used to
		throw here.
		"""
		try:
			master = layer.master
		except Exception:
			return 0.0
		if master is None:
			return 0.0
		try:
			angle = master.italicAngle
		except Exception:
			return 0.0
		if not isFiniteNumber(angle):
			return 0.0
		return angle

	@objc.python_method
	def cornerPointsOfSelectedObject(self, thisObject):
		"""
		Returns the points thisObject contributes to the selection bounds:
		the four corners of its bounding box (paths, components), or its
		position (nodes, anchors). Returns None if we cannot get either.
		"""
		try:
			rect = getattr(thisObject, "bounds", None)
			if rect is not None:
				x, y = rect.origin.x, rect.origin.y
				width, height = rect.size.width, rect.size.height
				if all(isFiniteNumber(value) for value in (x, y, width, height)):
					return (
						NSPoint(x, y),
						NSPoint(x + width, y),
						NSPoint(x, y + height),
						NSPoint(x + width, y + height),
					)
		except Exception:
			pass

		try:
			position = getattr(thisObject, "position", None)
			if position is not None and isFiniteNumber(position.x) and isFiniteNumber(position.y):
				return (NSPoint(position.x, position.y),)
		except Exception:
			pass

		return None

	@objc.python_method
	def centerOfSelectionPoints(self, selectedObjects, italicAngle=0.0):
		"""
		Computes the center of selectedObjects ourselves, back-slanting every
		point by italicAngle first, and re-slanting the resulting center.
		Used when layer.selectionBounds cannot be trusted, e.g. when a corner
		component is part of the selection.
		"""
		minX = minY = maxX = maxY = None
		for thisObject in selectedObjects:
			points = self.cornerPointsOfSelectedObject(thisObject)
			if not points:
				continue
			for thisPoint in points:
				if italicAngle:
					thisPoint = self.italicize(thisPoint, italicAngle=-italicAngle, pivotalY=0.0)
				if minX is None:
					minX = maxX = thisPoint.x
					minY = maxY = thisPoint.y
				else:
					minX = min(minX, thisPoint.x)
					maxX = max(maxX, thisPoint.x)
					minY = min(minY, thisPoint.y)
					maxY = max(maxY, thisPoint.y)

		if minX is None:
			return None

		center = NSMakePoint((minX + maxX) * 0.5, (minY + maxY) * 0.5)
		if italicAngle:
			center = self.italicize(center, italicAngle=italicAngle, pivotalY=0.0)
		return center

	@objc.python_method
	def middleOfLayerSelection(self, layer, italicAngle=None):
		"""
		Returns the center of the current selection of layer as an NSPoint,
		or None if there is nothing (usable) selected. Corner, cap, brush and
		segment components are skipped: they have no coordinates of their own,
		and in Glyphs 4 they show up in the selection as pseudo paths/nodes
		that throw when asked for bounds.
		"""
		if layer is None:
			return None

		if italicAngle is None:
			italicAngle = self.italicAngleOfLayer(layer)

		try:
			selection = list(layer.selection)
		except Exception as e:
			self.logOnce("selection", "ShowCenterLines: cannot read layer selection: %s" % e)
			return None

		if not selection:
			return None

		drawableObjects = [o for o in selection if not isCornerComponent(o)]
		if not drawableObjects:
			# selection consists exclusively of corner components: nothing to center
			return None

		if len(drawableObjects) == len(selection):
			# plain selection, so we can use the (faster) Glyphs API:
			center = self.centerViaGlyphsAPI(layer, italicAngle)
			if center is not None:
				return center

		# corner components present, or the API let us down: measure it ourselves
		return self.centerOfSelectionPoints(drawableObjects, italicAngle=italicAngle)

	@objc.python_method
	def centerViaGlyphsAPI(self, layer, italicAngle):
		"""
		Center of the layer selection as reported by Glyphs itself.
		Returns None if Glyphs cannot supply usable numbers.
		"""
		try:
			if italicAngle == 0:
				bounds = layer.selectionBounds
			else:
				bounds = layer.boundsOfSelectionAngle_(transform(skew=italicAngle))
			x, y = NSMidX(bounds), NSMidY(bounds)
		except Exception as e:
			self.logOnce("selectionBounds", "ShowCenterLines: falling back to manual selection bounds: %s" % e)
			return None

		if not (isFiniteNumber(x) and isFiniteNumber(y)):
			return None

		if italicAngle == 0:
			return NSMakePoint(x, y)
		return self.italicize(NSMakePoint(x, y), italicAngle=italicAngle, pivotalY=0.0)

	@objc.python_method
	def background(self, layer):
		# a reporter redraws constantly, so never let an exception escape:
		try:
			self.drawCenterLines(layer)
		except Exception as e:
			self.logOnce(
				"background",
				"ShowCenterLines: could not draw center lines: %s\n%s" % (e, traceback.format_exc()),
			)

	@objc.python_method
	def drawCenterLines(self, layer):
		if layer is None:
			return

		angle = self.italicAngleOfLayer(layer)
		center = self.middleOfLayerSelection(layer, italicAngle=angle)
		if center is None:
			return
		x, y = center.x, center.y

		try:
			scale = self.getScale()
		except Exception:
			scale = 1.0
		if not scale or not isFiniteNumber(scale):
			scale = 1.0

		NSColor.disabledControlTextColor().set()

		cross = NSBezierPath.bezierPath()
		if angle != 0:
			cross.moveToPoint_(self.italicize(NSPoint(x, y - 5000), italicAngle=angle, pivotalY=y))
			cross.lineToPoint_(self.italicize(NSPoint(x, y + 5000), italicAngle=angle, pivotalY=y))
		else:
			cross.moveToPoint_(NSPoint(x, y - 5000))
			cross.lineToPoint_(NSPoint(x, y + 5000))
		cross.moveToPoint_(NSPoint(x - 5000, y))
		cross.lineToPoint_(NSPoint(x + 5000, y))
		cross.setLineWidth_(1.0 / scale)
		# dash:
		# cross.setLineDash_count_phase_((2.0 / scale, 1.0 / scale), 2, 0)

		cross.stroke()

	@objc.python_method
	def conditionalContextMenus(self):
		menuItems = []
		try:
			font = Glyphs.font
			if font and len(font.selectedLayers) == 1:
				layer = font.selectedLayers[0]

				# Exactly one object is selected and it’s an anchor
				if layer.selection:
					# Return context menu item
					menuItems.append({
						'name': Glyphs.localize({
							'en': 'Add Center Lines as Guides',
							'de': 'Mittellinien als Hilfslinien hinzufügen',
							'es': 'Añadir lineas centrales como guías',
							'fr': 'Ajouter lignes centrales comme repères',
						}),
						'action': self.addCenterGuides_
					})
		except Exception as e:
			self.logOnce("contextMenu", "ShowCenterLines: cannot build context menu: %s" % e)
		return menuItems

	@objc.python_method
	def guideAtPointWithAngle(self, point, angle):
		try:
			g = GSGuide()
			g.position = point
			g.angle = angle
			return g
		except Exception as e:
			self.logToConsole("guideAtPointWithAngle: %s" % e)
			return None

	def addCenterGuides_(self, sender=None):
		try:
			if not Glyphs.font or len(Glyphs.font.selectedLayers) != 1:
				return
			layer = Glyphs.font.selectedLayers[0]
			center = self.middleOfLayerSelection(layer)
			if center is None:
				return
			italicAngle = 90 - self.italicAngleOfLayer(layer)

			# turn vertical line into guide:
			verticalGuide = self.guideAtPointWithAngle(center, italicAngle)
			if verticalGuide is not None:
				layer.guideLines.append(verticalGuide)

			# turn horizontal line into guide:
			horizontalGuide = self.guideAtPointWithAngle(center, 0)
			if horizontalGuide is not None:
				layer.guideLines.append(horizontalGuide)

			# enable View > Show Guides:
			if Glyphs.versionNumber >= 3.0:
				Glyphs.defaults["showGuides"] = 1
			else:
				Glyphs.defaults["showGuidelines"] = 1
		except Exception as e:
			self.logToConsole(
				"ShowCenterLines: could not add center guides: %s\n%s" % (e, traceback.format_exc())
			)

	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
