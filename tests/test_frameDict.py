from __future__ import absolute_import, division, print_function
import unittest

import numpy as np
from numpy.testing import assert_allclose

import astshim as ast
from astshim.test import MappingTestCase


class TestFrameDict(MappingTestCase):

    def setUp(self):
        self.frame1 = ast.Frame(2, "Domain=frame1")
        self.frame2 = ast.Frame(2, "Domain=frame2")
        self.zoom = 1.5
        self.zoomMap = ast.ZoomMap(2, self.zoom, "Ident=zoomMap")
        self.initialNumFrames = self.frame1.getNObject()  # may be >2 when run using pytest
        self.initialNumZoomMap = self.zoomMap.getNObject()  # may be > 1 when run using pytest

    def checkDict(self, frameDict):
        for index in range(1, frameDict.nFrame + 1):
            domain = frameDict.getFrame(index).domain
            self.assertEqual(frameDict.getIndex(domain), index)
            self.assertEqual(frameDict.getFrame(domain).domain, domain)

    def test_FrameDictOneFrameConstructor(self):
        frameDict = ast.FrameDict(self.frame1)
        self.assertIsInstance(frameDict, ast.FrameDict)
        self.assertEqual(frameDict.nFrame, 1)
        self.assertEqual(frameDict.getAllDomains(), ["FRAME1"])
        self.assertEqual(frameDict.getIndex("frame1"), 1)  # should be case blind

        with self.assertRaises(ValueError):
            frameDict.getIndex("missingDomain")
        with self.assertRaises(ValueError):
            frameDict.getIndex("")

        # Make sure the frame is deep copied
        self.frame1.domain = "NEWDOMAIN"
        self.assertEqual(frameDict.getFrame("FRAME1").domain, "FRAME1")
        self.assertEqual(frameDict.getFrame(frameDict.BASE).domain, "FRAME1")
        self.assertEqual(self.frame1.getRefCount(), 1)
        self.assertEqual(self.frame1.getNObject(), self.initialNumFrames + 1)

        # make sure BASE and CURRENT are available on the class and instance
        self.assertEqual(ast.FrameDict.BASE, frameDict.BASE)
        self.assertEqual(ast.FrameDict.CURRENT, frameDict.CURRENT)

        self.checkCopy(frameDict)

        indata = np.array([
            [0.0, 0.1, -1.5],
            [5.1, 0.0, 3.1],
        ])
        self.checkMappingPersistence(frameDict, indata)
        self.checkPersistence(frameDict)
        self.checkDict(frameDict)

    def testFrameDictFrameSetConstructor(self):
        frameSet = ast.FrameSet(self.frame1, self.zoomMap, self.frame2)
        frameDict = ast.FrameDict(frameSet)

        indata = np.array([[1.1, 2.1, 3.1], [1.2, 2.2, 3.2]])
        predictedOut = indata * self.zoom
        assert_allclose(frameDict.applyForward(indata), predictedOut)
        assert_allclose(frameDict.applyInverse(predictedOut), indata)

    def test_FrameDictAddFrame(self):
        self.initialNumFrames = self.frame1.getNObject()  # may be >1 when run using pytest
        frameDict = ast.FrameDict(self.frame1)

        self.assertEqual(self.frame1.getNObject(), self.initialNumFrames + 1)
        frameDict.addFrame(1, self.zoomMap, self.frame2)
        self.assertEqual(frameDict.nFrame, 2)
        self.frame2.domain = "NEWDOMAIN"
        self.assertEqual(frameDict.getFrame("FRAME2").domain, "FRAME2")
        self.assertEqual(frameDict.getFrame(frameDict.CURRENT).domain, "FRAME2")
        self.assertEqual(self.frame2.getRefCount(), 1)
        self.assertEqual(self.frame1.getNObject(), self.initialNumFrames + 2)

        # make sure all objects were deep copied
        self.frame1.domain = "newBase"
        self.zoomMap.ident = "newMapping"
        self.frame2.domain = "newCurrent"
        self.assertEqual(frameDict.getFrame(frameDict.BASE).domain, "FRAME1")
        self.assertEqual(frameDict.getFrame(frameDict.CURRENT).domain, "FRAME2")
        self.assertEqual(frameDict.getMapping().ident, "zoomMap")
        self.checkPersistence(frameDict)
        self.checkDict(frameDict)

    def testFrameDictFrameMappingFrameConstructor(self):
        frameDict = ast.FrameDict(self.frame1, self.zoomMap, self.frame2)
        self.assertEqual(frameDict.nFrame, 2)
        self.assertEqual(frameDict.base, 1)
        self.assertEqual(frameDict.getIndex("FRAME1"), 1)
        self.assertEqual(frameDict.current, 2)
        self.assertEqual(frameDict.getIndex("frame2"), 2)
        self.assertEqual(set(frameDict.getAllDomains()), set(["FRAME1", "FRAME2"]))

        # make sure all objects were deep copied
        self.frame1.domain = "newBase"
        self.zoomMap.ident = "newMapping"
        self.frame2.domain = "newCurrent"
        self.assertEqual(frameDict.getFrame(frameDict.BASE).domain, "FRAME1")
        self.assertEqual(frameDict.getFrame(frameDict.CURRENT).domain, "FRAME2")
        self.assertEqual(frameDict.getMapping().ident, "zoomMap")
        self.checkPersistence(frameDict)
        self.checkDict(frameDict)

    def test_FrameDictGetMapping(self):
        frameDict = ast.FrameDict(self.frame1, self.zoomMap, self.frame2)

        # make sure the zoomMap in frameDict is a deep copy of self.zoomMap
        self.zoomMap.ident = "newMappingIdent"
        zoomMapList = (  # all should be the same
            frameDict.getMapping(frameDict.BASE, frameDict.CURRENT),
            frameDict.getMapping("FRAME1", "FRAME2"),
            frameDict.getMapping(frameDict.BASE, "frame2"),
            frameDict.getMapping("frame1", frameDict.CURRENT),
        )
        for zoomMap in zoomMapList:
            self.assertEqual(zoomMap.ident, "zoomMap")
        self.assertEqual(self.zoomMap.getRefCount(), 1)

        # make sure the zoomMapList are retrieved in the right direction
        indata = np.array([[1.1, 2.1, 3.1], [1.2, 2.2, 3.2]])
        predictedOut = indata * self.zoom
        for zoomMap in zoomMapList:
            assert_allclose(zoomMap.applyForward(indata), predictedOut)

        # check that getMapping returns a deep copy
        for i, zoomMap in enumerate(zoomMapList):
            zoomMap.ident = "newIdent%s" % (i,)
            self.assertEqual(zoomMap.getRefCount(), 1)
        self.assertEqual(frameDict.getMapping().ident, "zoomMap")
        # 5 = 1 in frameDict plus 4 retrieved copies in zoomMapList
        self.assertEqual(self.zoomMap.getNObject(), self.initialNumZoomMap + 5)
        self.checkDict(frameDict)

    def test_FrameDictRemoveFrame(self):
        frameDict = ast.FrameDict(self.frame1, self.zoomMap, self.frame2)
        self.assertEqual(frameDict.getIndex("FRAME1"), 1)
        self.assertEqual(frameDict.getIndex("FRAME2"), 2)
        self.assertEqual(self.frame1.getNObject(), self.initialNumFrames + 2)
        self.assertEqual(self.zoomMap.getNObject(), self.initialNumZoomMap + 1)

        # remove the frame named "FRAME1", leaving the frame named "FRAME2"
        frameDict.removeFrame("FRAME1")
        self.assertEqual(frameDict.getAllDomains(), ["FRAME2"])
        self.assertEqual(frameDict.nFrame, 1)
        self.assertEqual(frameDict.getIndex("FRAME2"), 1)
        self.assertEqual(frameDict.getFrame("FRAME2").domain, "FRAME2")
        self.assertEqual(self.frame1.getNObject(), self.initialNumFrames + 1)
        self.assertEqual(self.zoomMap.getNObject(), self.initialNumZoomMap)
        frameDeep = frameDict.getFrame(1)
        self.assertEqual(frameDeep.domain, "FRAME2")

        # it is not allowed to remove the last frame
        with self.assertRaises(RuntimeError):
            frameDict.removeFrame(1)

        self.checkDict(frameDict)

    def test_FrameDictRemapFrame(self):
        for useDomainForRemapFrame in (False, True):
            frameDict = ast.FrameDict(self.frame1, self.zoomMap, self.frame2)

            indata = np.array([
                [0.0, 0.1, -1.5],
                [5.1, 0.0, 3.1],
            ])
            predictedOut1 = indata * self.zoom
            assert_allclose(frameDict.applyForward(indata), predictedOut1)
            assert_allclose(frameDict.applyInverse(predictedOut1), indata)
            self.checkMappingPersistence(frameDict, indata)

            shift = (0.5, -1.5)
            shiftMap = ast.ShiftMap(shift, "Ident=shift")
            initialNumShiftMap = shiftMap.getNObject()
            self.assertEqual(self.zoomMap.getNObject(), self.initialNumZoomMap + 1)
            if useDomainForRemapFrame:
                frameDict.remapFrame("FRAME1", shiftMap)
            else:
                frameDict.remapFrame(1, shiftMap)
            self.assertEqual(self.zoomMap.getNObject(), self.initialNumZoomMap + 1)
            self.assertEqual(shiftMap.getNObject(), initialNumShiftMap + 1)
            predictedOut2 = (indata.T - shift).T * self.zoom
            assert_allclose(frameDict.applyForward(indata), predictedOut2)
            assert_allclose(frameDict.applyInverse(predictedOut2), indata)

    def test_FrameDictPermutationSkyFrame(self):
        """Test permuting FrameDict axes using a SkyFrame

        Permuting the axes of the current frame of a frame set
        *in situ* (by calling `permAxes` on the frame set itself)
        should update the connected mappings.
        """
        # test with arbitrary values that will not be wrapped by SkyFrame
        x = 0.257
        y = 0.832
        frame1 = ast.Frame(2)
        unitMap = ast.UnitMap(2)
        frame2 = ast.SkyFrame()
        frameDict = ast.FrameDict(frame1, unitMap, frame2)
        self.assertAlmostEqual(frameDict.applyForward([x, y]), [x, y])
        self.assertAlmostEqual(frameDict.applyInverse([x, y]), [x, y])

        # permuting the axes of the current frame also permutes the mapping
        frameDict.permAxes([2, 1])
        self.assertAlmostEqual(frameDict.applyForward([x, y]), [y, x])
        self.assertAlmostEqual(frameDict.applyInverse([x, y]), [y, x])

        # permuting again puts things back
        frameDict.permAxes([2, 1])
        self.assertAlmostEqual(frameDict.applyForward([x, y]), [x, y])
        self.assertAlmostEqual(frameDict.applyInverse([x, y]), [x, y])

    def test_FrameDictPermutationUnequal(self):
        """Test permuting FrameDict axes with nIn != nOut

        Permuting the axes of the current frame of a frame set
        *in situ* (by calling `permAxes` on the frame set itself)
        should update the connected mappings.

        Make nIn != nOut in order to test DM-9899
        FrameDict.permAxes would fail if nIn != nOut
        """
        # Initial mapping: 3 inputs, 2 outputs: 1-1, 2-2, 3=z
        # Test using arbitrary values for x,y,z
        x = 75.1
        y = -53.2
        z = 0.123
        frame1 = ast.Frame(3)
        permMap = ast.PermMap([1, 2, -1], [1, 2], [z])
        frame2 = ast.Frame(2)
        frameDict = ast.FrameDict(frame1, permMap, frame2)
        self.assertAlmostEqual(frameDict.applyForward([x, y, z]), [x, y])
        self.assertAlmostEqual(frameDict.applyInverse([x, y]), [x, y, z])

        # permuting the axes of the current frame also permutes the mapping
        frameDict.permAxes([2, 1])
        self.assertAlmostEqual(frameDict.applyForward([x, y, z]), [y, x])
        self.assertAlmostEqual(frameDict.applyInverse([x, y]), [y, x, z])

        # permuting again puts things back
        frameDict.permAxes([2, 1])
        self.assertAlmostEqual(frameDict.applyForward([x, y, z]), [x, y])
        self.assertAlmostEqual(frameDict.applyInverse([x, y]), [x, y, z])

    def testFrameDictSetBaseCurrent(self):
        frameDict = ast.FrameDict(self.frame1, self.zoomMap, self.frame2)
        self.assertEqual(frameDict.base, 1)
        self.assertEqual(frameDict.current, 2)
        self.assertEqual(frameDict.getIndex("frame1"), 1)
        self.assertEqual(frameDict.getIndex("frame2"), 2)

        indata = np.array([
            [0.0, 0.1, -1.5],
            [5.1, 0.0, 3.1],
        ])
        predictedOut1 = indata.copy() * self.zoom
        assert_allclose(frameDict.applyForward(indata), predictedOut1)

        frameDict.setCurrent("FRAME1")
        self.assertEqual(frameDict.base, 1)
        self.assertEqual(frameDict.current, 1)
        self.assertEqual(frameDict.getIndex("FRAME1"), 1)
        self.assertEqual(frameDict.getIndex("FRAME2"), 2)

        predictedOutput2 = indata.copy()
        assert_allclose(frameDict.applyForward(indata), predictedOutput2)

        frameDict.setBase("FRAME2")
        self.assertEqual(frameDict.base, 2)
        self.assertEqual(frameDict.current, 1)
        self.assertEqual(frameDict.getIndex("FRAME1"), 1)
        self.assertEqual(frameDict.getIndex("FRAME2"), 2)

        predictedOutput3 = indata.copy() / self.zoom
        assert_allclose(frameDict.applyForward(indata), predictedOutput3)

    def testFrameDictSetDomain(self):
        frameDict = ast.FrameDict(self.frame1, self.zoomMap, self.frame2)
        frameDict.setCurrent("FRAME1")
        frameDict.setDomain("NEWFRAME1")
        self.assertEqual(set(frameDict.getAllDomains()), set(["NEWFRAME1", "FRAME2"]))
        self.assertEqual(frameDict.getIndex("newFrame1"), 1)
        self.assertEqual(frameDict.getIndex("FRAME2"), 2)

        frameDict.setCurrent("FRAME2")
        frameDict.setDomain("NEWFRAME2")
        self.assertEqual(set(frameDict.getAllDomains()), set(["NEWFRAME1", "NEWFRAME2"]))
        self.assertEqual(frameDict.getIndex("NEWFRAME1"), 1)
        self.assertEqual(frameDict.getIndex("NEWFRAME2"), 2)


if __name__ == "__main__":
    unittest.main()
