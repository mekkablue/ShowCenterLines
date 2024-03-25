# encoding: utf-8

###########################################################################################################
#
#
#	Reporter Plugin
#
#	Read the docs:
#	https://github.com/schriftgestalt/GlyphsSDK/tree/master/Python%20Templates/Reporter
#
#
###########################################################################################################

import objc
from math import radians, tan
from copy import copy
from Foundation import NSMidX, NSMidY, NSAffineTransform, NSAffineTransformStruct, NSMakePoint, NSPoint
from GlyphsApp import *
from GlyphsApp.plugins import *


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
		myTransform.translateXBy_yBy_(shiftX,shiftY)
	if skew:
		myTransform.shearXBy_(tan(radians(skew)))
	return myTransform


class ShowCenterLines(ReporterPlugin):
	
	@objc.python_method
	def settings(self):
		self.menuName = Glyphs.localize({
			'en': 'Center Lines',
			'de': 'Mittellinien',
			'es': 'lineas centrales',
			'fr': 'lignes centrales',
		})
	
	@objc.python_method
	def italicize( self, thisPoint, italicAngle=0.0, pivotalY=0.0 ):
		"""
		Returns the italicized position of an NSPoint 'thisPoint'
		for a given angle 'italicAngle' and the pivotal height 'pivotalY',
		around which the italic slanting is executed, usually half x-height.
		Usage: myPoint = italicize(myPoint,10,xHeight*0.5)
		"""
		x = thisPoint.x
		yOffset = thisPoint.y - pivotalY # calculate vertical offset
		italicAngle = radians( italicAngle ) # convert to radians
		tangens = tan( italicAngle ) # math.tan needs radians
		horizontalDeviance = tangens * yOffset # vertical distance from pivotal point
		x += horizontalDeviance # x of point that is yOffset from pivotal point
		return NSPoint( x, thisPoint.y )
	
	@objc.python_method
	def middleOfLayerSelection(self, layer):
		x = NSMidX( layer.selectionBounds )
		y = NSMidY( layer.selectionBounds )
		return NSMakePoint(x, y)
	
	@objc.python_method
	def background(self, layer):
		if layer.selection:
			NSColor.disabledControlTextColor().set()
			angle = layer.master.italicAngle
			
			if angle == 0:
				x, y = self.middleOfLayerSelection(layer)
			else:
				backSlantedSelectionBounds = layer.boundsOfSelectionAngle_(transform(skew=angle))
				centerOfBackSlantedBounds = NSMakePoint(
					NSMidX(backSlantedSelectionBounds),
					NSMidY(backSlantedSelectionBounds),
				)
				x, y = self.italicize(
					centerOfBackSlantedBounds,
					italicAngle=angle,
					pivotalY=0.0,
					)
			
			cross = NSBezierPath.bezierPath()
			if angle != 0:
				cross.moveToPoint_( self.italicize( NSPoint( x, y-5000 ), italicAngle=angle, pivotalY=y ) )
				cross.lineToPoint_( self.italicize( NSPoint( x, y+5000 ), italicAngle=angle, pivotalY=y ) )
			else:
				cross.moveToPoint_( NSPoint( x, y-5000 ) )
				cross.lineToPoint_( NSPoint( x, y+5000 ) )
			cross.moveToPoint_( NSPoint( x-5000, y ) )
			cross.lineToPoint_( NSPoint( x+5000, y ) )
			cross.setLineWidth_(1.0/self.getScale())
			# dash:
			# cross.setLineDash_count_phase_( (2.0/self.getScale(),1.0/self.getScale()), 2, 0 )
			
			cross.stroke()


	@objc.python_method
	def conditionalContextMenus(self):
		menuItems = []
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
		return menuItems


	@objc.python_method
	def guideAtPointWithAngle( self, point, angle ):
		try:
			if Glyphs.versionNumber >= 3:
				# GLYPHS 3
				g = GSGuide()
			else:
				# GLYPHS 2
				g = GSGuideLine()
			g.position = point
			g.angle = angle
			return g
		except Exception as e:
			self.logToConsole(f"guideAtPointWithAngle: {str(e)}")
			return None

	def addCenterGuides_(self, sender=None):
		if Glyphs.font and len(Glyphs.font.selectedLayers) == 1:
			layer = Glyphs.font.selectedLayers[0]
			if layer.selection:
				center = self.middleOfLayerSelection(layer)
				italicAngle = 90-layer.master.italicAngle
				
				# turn vertical line into guide:
				layer.guideLines.append(self.guideAtPointWithAngle( center, italicAngle ))
				
				# turn horizontal line into guide:
				layer.guideLines.append(self.guideAtPointWithAngle( center, 0 ))
				
				# enable View > Show Guides:
				if Glyphs.versionNumber >= 3.0:
					Glyphs.defaults["showGuides"] = 1
				else:
					Glyphs.defaults["showGuidelines"] = 1
	
	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
