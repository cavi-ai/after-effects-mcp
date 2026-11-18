$.evalFile(new File(CAVI_LIB));

// Writes one PNG per time with Comp.saveFrameToPng; with background, a temporary solid of the comp's background color sits under the layers.
(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), i, backdrop = a.background ? caviBackdrop(comp) : null;
    for (i = 0; i < a.frames.length; i++) {
        comp.saveFrameToPng(a.frames[i].time, new File(a.frames[i].file));
    }
    if (backdrop) { caviDropBackdrop(backdrop); }
    caviReport({comp: comp.name, frames: a.frames.length, errors: []});
})();
