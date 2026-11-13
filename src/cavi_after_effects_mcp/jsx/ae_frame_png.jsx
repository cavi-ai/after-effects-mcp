$.evalFile(new File(CAVI_LIB));

// Writes one PNG per time with Comp.saveFrameToPng; with background, a temporary solid of the comp's background color sits under the layers.
(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), i, backdrop = null, source;
    if (a.background) {
        backdrop = comp.layers.addSolid(comp.bgColor, "cavi-frame-bg", comp.width, comp.height, comp.pixelAspect, comp.duration);
        backdrop.moveToEnd();
    }
    for (i = 0; i < a.frames.length; i++) {
        comp.saveFrameToPng(a.frames[i].time, new File(a.frames[i].file));
    }
    if (backdrop) {
        source = backdrop.source;
        backdrop.remove();
        if (source.usedIn.length === 0) { source.remove(); }
    }
    caviReport({comp: comp.name, frames: a.frames.length, errors: []});
})();
