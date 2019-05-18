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

	def settings(self):
		self.menuName = Glyphs.localize({
			'en': u'Center Lines',
			'de': u'Mittellinien',
			'es': u'lineas centrales',
			'fr': u'lignes centrales',
		})
	
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
	
		
	def background(self, layer):
		if layer.selection:
			NSColor.controlColor().set()

			x = NSMidX( layer.selectionBounds )
			y = NSMidY( layer.selectionBounds )
			
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

	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
