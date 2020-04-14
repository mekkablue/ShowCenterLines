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
from Foundation import NSMidX, NSMidY
from GlyphsApp import *
from GlyphsApp.plugins import *

class ShowCenterLines(ReporterPlugin):
	
	@objc.python_method
	def settings(self):
		self.menuName = Glyphs.localize({
			'en': u'Center Lines',
			'de': u'Mittellinien',
			'es': u'lineas centrales',
			'fr': u'lignes centrales',
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

			x, y = self.middleOfLayerSelection(layer)
			
			cross = NSBezierPath.bezierPath()
			angle = layer.master.italicAngle
			if angle:
				cross.moveToPoint_( self.italicize( NSPoint( x, y-5000 ), angle, y ) )
				cross.lineToPoint_( self.italicize( NSPoint( x, y+5000 ), angle, y ) )
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
							'en': u'Add Center Lines as Guides', 
							'de': u'Mittellinien als Hilfslinien hinzufügen',
							'es': u'Añadir lineas centrales como guías',
							'fr': u'Ajouter lignes centrales comme repères',
						}), 
					'action': self.addCenterGuides_
				})
		return menuItems


	@objc.python_method
	def guideAtPointWithAngle( self, point, angle ):
		try:
			try:
				# GLYPHS 3
				g = GSGuide()
			except:
				# GLYPHS 2
				g = GSGuideLine()
			g.position = point
			g.angle = angle
			return g
		except Exception as e:
			self.logToConsole( "guideAtPointWithAngle: %s" % str(e) )
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
