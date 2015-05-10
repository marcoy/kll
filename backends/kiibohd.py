#!/usr/bin/env python3
# KLL Compiler - Kiibohd Backend
#
# Backend code generator for the Kiibohd Controller firmware.
#
# Copyright (C) 2014-2015 by Jacob Alexander
#
# This file is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This file is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this file.  If not, see <http://www.gnu.org/licenses/>.

### Imports ###

import os
import sys
import re

from datetime import date

# Modifying Python Path, which is dumb, but the only way to import up one directory...
sys.path.append( os.path.expanduser('..') )

from kll_lib.backends import *
from kll_lib.containers import *
from kll_lib.hid_dict   import *


### Classes ###

class Backend( BackendBase ):
	# Default templates and output files
	templatePaths = ["templates/kiibohdKeymap.h", "templates/kiibohdDefs.h"]
	outputPaths = ["generatedKeymap.h", "kll_defs.h"]

	requiredCapabilities = {
		'CONS' : 'consCtrlOut',
		'NONE' : 'noneOut',
		'SYS'  : 'sysCtrlOut',
		'USB'  : 'usbKeyOut',
	}

	# Capability Lookup
	def capabilityLookup( self, type ):
		return self.requiredCapabilities[ type ];


	# TODO
	def layerInformation( self, name, date, author ):
		self.fill_dict['Information'] += "//  Name:    {0}\n".format( "TODO" )
		self.fill_dict['Information'] += "//  Version: {0}\n".format( "TODO" )
		self.fill_dict['Information'] += "//  Date:    {0}\n".format( "TODO" )
		self.fill_dict['Information'] += "//  Author:  {0}\n".format( "TODO" )


	# Processes content for fill tags and does any needed dataset calculations
	def process( self, capabilities, macros, variables, gitRev, gitChanges ):
		# Build string list of compiler arguments
		compilerArgs = ""
		for arg in sys.argv:
			if "--" in arg or ".py" in arg:
				compilerArgs += "//    {0}\n".format( arg )
			else:
				compilerArgs += "//      {0}\n".format( arg )

		# Build a string of modified files, if any
		gitChangesStr = "\n"
		if len( gitChanges ) > 0:
			for gitFile in gitChanges:
				gitChangesStr += "//    {0}\n".format( gitFile )
		else:
			gitChangesStr = "    None\n"

		# Prepare BaseLayout and Layer Info
		baseLayoutInfo = ""
		defaultLayerInfo = ""
		partialLayersInfo = ""
		for file, name in zip( variables.baseLayout['*LayerFiles'], variables.baseLayout['*NameStack'] ):
			baseLayoutInfo += "//    {0}\n//      {1}\n".format( name, file )
		if '*LayerFiles' in variables.layerVariables[0].keys():
			for file, name in zip( variables.layerVariables[0]['*LayerFiles'], variables.layerVariables[0]['*NameStack'] ):
				defaultLayerInfo += "//    {0}\n//      {1}\n".format( name, file )
		if '*LayerFiles' in variables.layerVariables[1].keys():
			for layer in range( 1, len( variables.layerVariables ) ):
				partialLayersInfo += "//    Layer {0}\n".format( layer )
				if len( variables.layerVariables[ layer ]['*LayerFiles'] ) > 0:
					for file, name in zip( variables.layerVariables[ layer ]['*LayerFiles'], variables.layerVariables[ layer ]['*NameStack'] ):
						partialLayersInfo += "//     {0}\n//       {1}\n".format( name, file )


		## Information ##
		self.fill_dict['Information']  = "// This file was generated by the kll compiler, DO NOT EDIT.\n"
		self.fill_dict['Information'] += "// Generation Date:    {0}\n".format( date.today() )
		self.fill_dict['Information'] += "// KLL Backend:        {0}\n".format( "kiibohd" )
		self.fill_dict['Information'] += "// KLL Git Rev:        {0}\n".format( gitRev )
		self.fill_dict['Information'] += "// KLL Git Changes:{0}".format( gitChangesStr )
		self.fill_dict['Information'] += "// Compiler arguments:\n{0}".format( compilerArgs )
		self.fill_dict['Information'] += "//\n"
		self.fill_dict['Information'] += "// - Base Layer -\n{0}".format( baseLayoutInfo )
		self.fill_dict['Information'] += "// - Default Layer -\n{0}".format( defaultLayerInfo )
		self.fill_dict['Information'] += "// - Partial Layers -\n{0}".format( partialLayersInfo )


		## Variable Information ##
		self.fill_dict['VariableInformation'] = ""

		# Iterate through the variables, output, and indicate the last file that modified it's value
		# Output separate tables per file, per table and overall
		# TODO


		## Defines ##
		self.fill_dict['Defines'] = ""

		# Iterate through defines and lookup the variables
		for define in variables.defines.keys():
			if define in variables.overallVariables.keys():
				self.fill_dict['Defines'] += "\n#define {0} {1}".format( variables.defines[ define ], variables.overallVariables[ define ] )
			else:
				print( "{0} '{1}' not defined...".format( WARNING, define ) )


		## Capabilities ##
		self.fill_dict['CapabilitiesList'] = "const Capability CapabilitiesList[] = {\n"

		# Keys are pre-sorted
		for key in capabilities.keys():
			funcName = capabilities.funcName( key )
			argByteWidth = capabilities.totalArgBytes( key )
			self.fill_dict['CapabilitiesList'] += "\t{{ {0}, {1} }},\n".format( funcName, argByteWidth )

		self.fill_dict['CapabilitiesList'] += "};"


		## Results Macros ##
		self.fill_dict['ResultMacros'] = ""

		# Iterate through each of the result macros
		for result in range( 0, len( macros.resultsIndexSorted ) ):
			self.fill_dict['ResultMacros'] += "Guide_RM( {0} ) = {{ ".format( result )

			# Add the result macro capability index guide (including capability arguments)
			# See kiibohd controller Macros/PartialMap/kll.h for exact formatting details
			for sequence in range( 0, len( macros.resultsIndexSorted[ result ] ) ):
				# If the sequence is longer than 1, prepend a sequence spacer
				# Needed for USB behaviour, otherwise, repeated keys will not work
				if sequence > 0:
					# <single element>, <usbCodeSend capability>, <USB Code 0x00>
					self.fill_dict['ResultMacros'] += "1, {0}, 0x00, ".format( capabilities.getIndex( self.capabilityLookup('USB') ) )

				# For each combo in the sequence, add the length of the combo
				self.fill_dict['ResultMacros'] += "{0}, ".format( len( macros.resultsIndexSorted[ result ][ sequence ] ) )

				# For each combo, add each of the capabilities used and their arguments
				for combo in range( 0, len( macros.resultsIndexSorted[ result ][ sequence ] ) ):
					resultItem = macros.resultsIndexSorted[ result ][ sequence ][ combo ]

					# Add the capability index
					self.fill_dict['ResultMacros'] += "{0}, ".format( capabilities.getIndex( resultItem[0] ) )

					# Add each of the arguments of the capability
					for arg in range( 0, len( resultItem[1] ) ):
						# Special cases
						if isinstance( resultItem[1][ arg ], str ):
							# If this is a CONSUMER_ element, needs to be split into 2 elements
							if re.match( '^CONSUMER_', resultItem[1][ arg ] ):
								tag = resultItem[1][ arg ].split( '_', 1 )[1]
								if '_' in tag:
									tag = tag.replace( '_', '' )
								lookupNum = kll_hid_lookup_dictionary['ConsCode'][ tag ][1]
								byteForm = lookupNum.to_bytes( 2, byteorder='little' ) # XXX Yes, little endian from how the uC structs work
								self.fill_dict['ResultMacros'] += "{0}, {1}, ".format( *byteForm )
								continue

							# None, fall-through disable
							elif resultItem[0] is self.capabilityLookup('NONE'):
								continue

						self.fill_dict['ResultMacros'] += "{0}, ".format( resultItem[1][ arg ] )

			# If sequence is longer than 1, append a sequence spacer at the end of the sequence
			# Required by USB to end at sequence without holding the key down
			if len( macros.resultsIndexSorted[ result ] ) > 1:
				# <single element>, <usbCodeSend capability>, <USB Code 0x00>
				self.fill_dict['ResultMacros'] += "1, {0}, 0x00, ".format( capabilities.getIndex( self.capabilityLookup('USB') ) )

			# Add list ending 0 and end of list
			self.fill_dict['ResultMacros'] += "0 };\n"
		self.fill_dict['ResultMacros'] = self.fill_dict['ResultMacros'][:-1] # Remove last newline


		## Result Macro List ##
		self.fill_dict['ResultMacroList'] = "const ResultMacro ResultMacroList[] = {\n"

		# Iterate through each of the result macros
		for result in range( 0, len( macros.resultsIndexSorted ) ):
			self.fill_dict['ResultMacroList'] += "\tDefine_RM( {0} ),\n".format( result )
		self.fill_dict['ResultMacroList'] += "};"


		## Result Macro Record ##
		self.fill_dict['ResultMacroRecord'] = "ResultMacroRecord ResultMacroRecordList[ ResultMacroNum ];"


		## Trigger Macros ##
		self.fill_dict['TriggerMacros'] = ""

		# Iterate through each of the trigger macros
		for trigger in range( 0, len( macros.triggersIndexSorted ) ):
			self.fill_dict['TriggerMacros'] += "Guide_TM( {0} ) = {{ ".format( trigger )

			# Add the trigger macro scan code guide
			# See kiibohd controller Macros/PartialMap/kll.h for exact formatting details
			for sequence in range( 0, len( macros.triggersIndexSorted[ trigger ][ 0 ] ) ):
				# For each combo in the sequence, add the length of the combo
				self.fill_dict['TriggerMacros'] += "{0}, ".format( len( macros.triggersIndexSorted[ trigger ][0][ sequence ] ) )

				# For each combo, add the key type, key state and scan code
				for combo in range( 0, len( macros.triggersIndexSorted[ trigger ][ 0 ][ sequence ] ) ):
					triggerItem = macros.triggersIndexSorted[ trigger ][ 0 ][ sequence ][ combo ]

					# TODO Add support for Analog keys
					# TODO Add support for LED states
					self.fill_dict['TriggerMacros'] += "0x00, 0x01, 0x{0:02X}, ".format( triggerItem )

			# Add list ending 0 and end of list
			self.fill_dict['TriggerMacros'] += "0 };\n"
		self.fill_dict['TriggerMacros'] = self.fill_dict['TriggerMacros'][ :-1 ] # Remove last newline


		## Trigger Macro List ##
		self.fill_dict['TriggerMacroList'] = "const TriggerMacro TriggerMacroList[] = {\n"

		# Iterate through each of the trigger macros
		for trigger in range( 0, len( macros.triggersIndexSorted ) ):
			# Use TriggerMacro Index, and the corresponding ResultMacro Index
			self.fill_dict['TriggerMacroList'] += "\tDefine_TM( {0}, {1} ),\n".format( trigger, macros.triggersIndexSorted[ trigger ][1] )
		self.fill_dict['TriggerMacroList'] += "};"


		## Trigger Macro Record ##
		self.fill_dict['TriggerMacroRecord'] = "TriggerMacroRecord TriggerMacroRecordList[ TriggerMacroNum ];"


		## Max Scan Code ##
		self.fill_dict['MaxScanCode'] = "#define MaxScanCode 0x{0:X}".format( macros.overallMaxScanCode )


		## Default Layer and Default Layer Scan Map ##
		self.fill_dict['DefaultLayerTriggerList'] = ""
		self.fill_dict['DefaultLayerScanMap'] = "const nat_ptr_t *default_scanMap[] = {\n"

		# Iterate over triggerList and generate a C trigger array for the default map and default map array
		for triggerList in range( macros.firstScanCode[ 0 ], len( macros.triggerList[ 0 ] ) ):
			# Generate ScanCode index and triggerList length
			self.fill_dict['DefaultLayerTriggerList'] += "Define_TL( default, 0x{0:02X} ) = {{ {1}".format( triggerList, len( macros.triggerList[ 0 ][ triggerList ] ) )

			# Add scanCode trigger list to Default Layer Scan Map
			self.fill_dict['DefaultLayerScanMap'] += "default_tl_0x{0:02X}, ".format( triggerList )

			# Add each item of the trigger list
			for trigger in macros.triggerList[ 0 ][ triggerList ]:
				self.fill_dict['DefaultLayerTriggerList'] += ", {0}".format( trigger )

			self.fill_dict['DefaultLayerTriggerList'] += " };\n"
		self.fill_dict['DefaultLayerTriggerList'] = self.fill_dict['DefaultLayerTriggerList'][:-1] # Remove last newline
		self.fill_dict['DefaultLayerScanMap'] = self.fill_dict['DefaultLayerScanMap'][:-2] # Remove last comma and space
		self.fill_dict['DefaultLayerScanMap'] += "\n};"


		## Partial Layers and Partial Layer Scan Maps ##
		self.fill_dict['PartialLayerTriggerLists'] = ""
		self.fill_dict['PartialLayerScanMaps'] = ""

		# Iterate over each of the layers, excluding the default layer
		for layer in range( 1, len( macros.triggerList ) ):
			# Prepare each layer
			self.fill_dict['PartialLayerScanMaps'] += "// Partial Layer {0}\n".format( layer )
			self.fill_dict['PartialLayerScanMaps'] += "const nat_ptr_t *layer{0}_scanMap[] = {{\n".format( layer )
			self.fill_dict['PartialLayerTriggerLists'] += "// Partial Layer {0}\n".format( layer )

			# Iterate over triggerList and generate a C trigger array for the layer
			for triggerList in range( macros.firstScanCode[ layer ], len( macros.triggerList[ layer ] ) ):
				# Generate ScanCode index and triggerList length
				self.fill_dict['PartialLayerTriggerLists'] += "Define_TL( layer{0}, 0x{1:02X} ) = {{ {2}".format( layer, triggerList, len( macros.triggerList[ layer ][ triggerList ] ) )

				# Add scanCode trigger list to Default Layer Scan Map
				self.fill_dict['PartialLayerScanMaps'] += "layer{0}_tl_0x{1:02X}, ".format( layer, triggerList )

				# Add each item of the trigger list
				for trigger in macros.triggerList[ layer ][ triggerList ]:
					self.fill_dict['PartialLayerTriggerLists'] += ", {0}".format( trigger )

				self.fill_dict['PartialLayerTriggerLists'] += " };\n"
			self.fill_dict['PartialLayerTriggerLists'] += "\n"
			self.fill_dict['PartialLayerScanMaps'] = self.fill_dict['PartialLayerScanMaps'][:-2] # Remove last comma and space
			self.fill_dict['PartialLayerScanMaps'] += "\n};\n\n"
		self.fill_dict['PartialLayerTriggerLists'] = self.fill_dict['PartialLayerTriggerLists'][:-2] # Remove last 2 newlines
		self.fill_dict['PartialLayerScanMaps'] = self.fill_dict['PartialLayerScanMaps'][:-2] # Remove last 2 newlines


		## Layer Index List ##
		self.fill_dict['LayerIndexList'] = "const Layer LayerIndex[] = {\n"

		# Iterate over each layer, adding it to the list
		for layer in range( 0, len( macros.triggerList ) ):
			# Lookup first scancode in map
			firstScanCode = macros.firstScanCode[ layer ]

			# Generate stacked name
			stackName = ""
			if '*NameStack' in variables.layerVariables[ layer ].keys():
				for name in range( 0, len( variables.layerVariables[ layer ]['*NameStack'] ) ):
					stackName += "{0} + ".format( variables.layerVariables[ layer ]['*NameStack'][ name ] )
				stackName = stackName[:-3]

			# Default map is a special case, always the first index
			if layer == 0:
				self.fill_dict['LayerIndexList'] += '\tLayer_IN( default_scanMap, "D: {1}", 0x{0:02X} ),\n'.format( firstScanCode, stackName )
			else:
				self.fill_dict['LayerIndexList'] += '\tLayer_IN( layer{0}_scanMap, "{0}: {2}", 0x{1:02X} ),\n'.format( layer, firstScanCode, stackName )
		self.fill_dict['LayerIndexList'] += "};"


		## Layer State ##
		self.fill_dict['LayerState'] = "uint8_t LayerState[ LayerNum ];"

