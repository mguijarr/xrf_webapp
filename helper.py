import sys
from fisx import Elements
from fisx import Material
from fisx import Detector
from fisx import XRF
DEBUG = 1

def getElementsInstance():
    elementsInstance = Elements()
    elementsInstance.initializeAsPyMca()
    return elementsInstance

DEFAULT_INSTANCE = None

def _getFisxMaterials(webConfiguration, elementsInstance=None):
    """
    Given a user configuration, return the list of fisx materials to be
    used by the library for calculation purposes.
    """
    if elementsInstance is None:
        elementsInstance = getElementsInstance()

    # define all the needed materials
    # Web to module translator to simplify updates
    Thickness = "thickness"
    Density = "density"
    CompoundList = "compounds"
    CompoundFraction = "mass"
    Comment = "comment"
    Name = "name"
    
    inputMaterialList = webConfiguration.get("materials", [])
    nMaterials = len(inputMaterialList)
    fisxMaterials = []
    processedMaterialList = []

    lastProcessedMaterial = None
    while (len(processedMaterialList) != nMaterials):
        for i in range(nMaterials):
            inputMaterialDict = inputMaterialList[i]
            materialName = inputMaterialDict[Name]
            if materialName in processedMaterialList:
                # already defined
                pass
            elif lastProcessedMaterial == materialName:
                # prevent endless loop
                if not totallyDefined:
                    raise ValueError("Material '%s' not totally defined")
            else:
                thickness = inputMaterialDict.get(Thickness, 1.0)
                density = inputMaterialDict.get(Density, 1.0)
                comment = inputMaterialDict.get(Comment, "")
                if not len(comment):
                    comment = ""
                compoundList = inputMaterialDict[CompoundList]
                fractionList = inputMaterialDict[CompoundFraction]
                if not hasattr(fractionList, "__getitem__"):
                    compoundList = [compoundList]
                    fractionList = [fractionList]
                composition = {}
                for n in range(len(compoundList)):
                    composition[compoundList[n]] = float(fractionList[n])
                # check the composition is expressed in terms of elements
                # and not in terms of other undefined materials
                totallyDefined = True
                for element in composition:
                    #check if it can be understood
                    if not len(elementsInstance.getComposition(element)):
                        # compound not understood
                        # probably we have a material defined in terms of other material
                        totallyDefined = False
                if totallyDefined:
                    try:
                        fisxMaterial = Material(materialName,
                                              density=float(density),
                                              thickness=float(thickness),
                                              comment=comment)
                        fisxMaterial.setComposition(composition)
                        fisxMaterials.append(fisxMaterial)
                    except:
                        text = "Error defining material %s" % \
                                        materialName
                        text += "\n" + "%s" % (sys.exc_info()[1])
                        raise TypeError(text)
                    processedMaterialList.append(materialName)
            lastProcessedMaterial = materialName
    return fisxMaterials

def _getBeamParameters(webConfiguration):
    # Translation dictionnary
    Energy = "beam_energy"
    
    inputEnergy = webConfiguration[Energy]
    if inputEnergy in [None, ""]:
        raise ValueError("Beam energy has to be specified")
    energyList = [float(inputEnergy)]
    weightList = [1.0]
    characteristicList = [1]
    return energyList, weightList, characteristicList

def _getBeamFilters(webConfiguration):
    """
    Due to wrapping constraints, the filter list must have the form:
    [[Material name or formula0, density0, thickness0, funny factor0],
     [Material name or formula1, density1, thickness1, funny factor1],
     ...
     [Material name or formulan, densityn, thicknessn, funny factorn]]
    """
    # Translation dictionnary
    return []

def _getAttenuators(webConfiguration):
    """
    Due to wrapping constraints, the filter list must have the form:
    [[Material name or formula0, density0, thickness0, funny factor0],
     [Material name or formula1, density1, thickness1, funny factor1],
     ...
     [Material name or formulan, densityn, thicknessn, funny factorn]]
    """
    # Translation dictionnary
    return []

def _getSampleParameters(webConfiguration):
    """
    Due to wrapping constraints, output list must have the form:
    [[Material name or formula0, density0, thickness0, funny factor0],
     [Material name or formula1, density1, thickness1, funny factor1],
     ...
     [Material name or formulan, densityn, thicknessn, funny factorn]]

    """
    # Translation dictionnary
    Thickness = "thickness"
    Density = "density"
    Material = "material"
    Name = "name"

    # Extract the parameters
    multilayerSample = []    
    counter = 0
    for layer in webConfiguration['multilayer']:
        try:
            name = layer.get(Name, "Layer%d" % counter)
            material = layer[Material]
            density = float(layer[Density])
            thickness = float(layer[Thickness])
            funny = 1.0
            multilayerSample.append([material, density, thickness, funny])
        except:
            text = "Error defining sample %s" % name
            text += "\n" + ("%s" % sys.exc_info()[1])
            raise ValueError(text)
        counter += 1
    return multilayerSample

def _getDetector(webConfiguration):
    # Detector is described as a list [material, density, thickness]
    # Translation dictionnary
    Thickness = "thickness"
    Density = "density"
    Material = "material"
    Area = "area"
    Distance = "distance"
    material = webConfiguration["detector"].get(Material, None)
    if material is None:
        # No detector
        return None
    else:
        density = float(webConfiguration["detector"][Density])
        thickness = float(webConfiguration["detector"][Thickness])
        area = float(webConfiguration["detector"][Area])
        distance = float(webConfiguration["detector"][Distance])
        detectorInstance = Detector(material, density, thickness)
        detectorInstance.setActiveArea(area)
        detectorInstance.setDistance(distance)
    return detectorInstance

def getMultilayerFluorescence(webConfiguration, elementsInstance=None):
    if elementsInstance is None:
        global DEFAULT_INSTANCE
        if DEFAULT_INSTANCE is None:
            DEFAULT_INSTANCE = getElementsInstance()
        elementsInstance = DEFAULT_INSTANCE

    # Materials used in the description
    elementsInstance.removeMaterials()
    materials = _getFisxMaterials(webConfiguration, elementsInstance)
    for material in materials:
        if DEBUG:
            print("Adding material making sure not to have duplicates")
        elementsInstance.addMaterial(material, errorOnReplace=1)

    # The beam energy for the time being is just a single energy
    energyList, weightList, characteristicList = _getBeamParameters( \
                                                    webConfiguration)
    if not len(energyList):
        raise ValueError("Empty list of beam energies!!!")

    xrf = XRF()
    if DEBUG:
        print("setting beam")
    xrf.setBeam(energyList, weights=weightList,
                            characteristic=characteristicList)

    # beam filters
    beamFilters = _getBeamFilters(webConfiguration)
    if len(beamFilters):
        if DEBUG:
            print("setting beam filters")
        xrf.setBeamFilters(beamFilters)

    # the sample description
    if DEBUG:
        print("getting sample parameters")
    multilayerSample = _getSampleParameters(webConfiguration)
    if DEBUG:
        print("setting sample")
    xrf.setSample(multilayerSample)

    # the geometry
    if DEBUG:
        print("setting geometry")
    alphaIn = float(webConfiguration["incoming_angle"])
    alphaOut = float(webConfiguration["outgoing_angle"])
    xrf.setGeometry(alphaIn, alphaOut)

    # the detector
    if DEBUG:
        print("getting detector instance")
    detectorInstance = _getDetector(webConfiguration)
    if detectorInstance is not None:
        xrf.setDetector(detectorInstance)
        useGeometricEfficiency = 1
    else:
        useGeometricEfficiency = 0

    # the pics to look for
    elementNames = elementsInstance.getElementNames()
    peakFamilies = ["K", "KA", "KB",
                    "L", "L1", "L2", "L3",
                    "M"]
    peakList = []
    for peakDict in webConfiguration["peaks"]:
        # element
        ele = peakDict["element"].strip()
        if not len(ele):
            raise ValueError("Empty element name")
        elif ele not in elementNames:
            raise ValueError("Invalid element name: <%s>"  % ele)

        # family
        family = peakDict["family"].strip().upper()
        if not len(family):
            raise ValueError("Empty peak family")
        elif family not in peakFamilies:
            raise ValueError("Invalid peak family: <%s>"  % ele)
        peak = ele + " " + family

        # layer if requested
        layer = peakDict.get("layer").strip().upper()
        if layer.upper() not in ["", "NONE", "ANY"]:
            layer = int(layer)
            peak = peak + " " + "%02d" % layer
        peakList.append(peak)
    if not len(peakList):
        raise ValueError("Please specify peaks")

    expectedFluorescence = xrf.getMultilayerFluorescence(peakList,
                            elementsInstance,
                            secondary=2,
                            useGeometricEfficiency=useGeometricEfficiency,
                            useMassFractions=0,
                            secondaryCalculationLimit=0.0)

    return getTextOutput(expectedFluorescence)

def getTextOutput(expectedFluorescence):
    fluo = expectedFluorescence
    text = ""
    text = "Element   Peak            Energy    Secondary   Tertiary Rate/MassFraction Rate"
    text += "\n"
    for key in fluo:
        for layer in fluo[key]:
            peakList = list(fluo[key][layer].keys())
            peakList.sort()
            for peak in peakList:
                # mass fraction
                if "massFraction" in fluo[key][layer][peak]:
                    massFraction = fluo[key][layer][peak]["massFraction"]
                elif "esc" not in peak:
                    raise KeyError("Peak %s misses mass fraction information" \
                                   % peak)
                # energy of the peak
                energy = fluo[key][layer][peak]["energy"]
                # expected measured rate per unit mass fraction
                rate = fluo[key][layer][peak]["rate"]
                actualRate = rate * massFraction
                # primary photons (no attenuation and no detector considered)
                primary = fluo[key][layer][peak]["primary"]
                # secondary photons (no attenuation and no detector considered)
                secondary = fluo[key][layer][peak]["secondary"]
                # tertiary photons (no attenuation and no detector considered)
                tertiary = fluo[key][layer][peak].get("tertiary", 0.0)
                # correction due to secondary excitation
                enhancement2 = (primary + secondary) / primary
                enhancement3 = (primary + secondary + tertiary) / primary
                text += ("%s   %s    %7.4f     %.5f    %.5f     %.3e     %.3e" % \
                                   (key, peak + (14 - len(peak)) * " ", energy,
                                   enhancement2, enhancement3, rate, actualRate))
                text += "\n"
    return text

if __name__ == "__main__":
    DEBUG = 1
    import time
    import sys
    if len(sys.argv) < 2:
        print("Usage: python FisxHelper FitConfigurationFile [element] [matrix_flag]")
        sys.exit(0)
    fileName = sys.argv[1]
    if len(sys.argv) > 2:
        element = sys.argv[2]
        if len(sys.argv) > 3:
            matrix = int(sys.argv[3])    
            print(getFisxCorrectionFactorsFromFitConfigurationFile(\
                fileName, elementsFromMatrix=matrix))[element]
        else:
            print(getFisxCorrectionFactorsFromFitConfigurationFile(fileName)) \
                                                                    [element]
    else:
        print(getFisxCorrectionFactorsFromFitConfigurationFile(fileName))

