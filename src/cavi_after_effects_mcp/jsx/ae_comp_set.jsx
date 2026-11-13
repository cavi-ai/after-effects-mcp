$.evalFile(new File(CAVI_LIB));

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), source = comp, renderers = [], i;
    if (a.duplicate_as !== null) {
        comp = comp.duplicate();
        comp.name = a.duplicate_as;
    }
    if (a.name !== null) { comp.name = a.name; }
    if (a.width !== null || a.height !== null) {
        comp.width = a.width !== null ? a.width : comp.width;
        comp.height = a.height !== null ? a.height : comp.height;
    }
    if (a.fps !== null) { comp.frameRate = a.fps; }
    if (a.duration !== null) { comp.duration = a.duration; }
    if (a.work_area !== null) {
        comp.workAreaStart = a.work_area[0];
        comp.workAreaDuration = a.work_area[1];
    }
    if (a.background !== null) { comp.bgColor = a.background; }
    if (a.renderer !== null) {
        for (i = 0; i < comp.renderers.length; i++) { renderers.push(comp.renderers[i]); }
        if (("," + renderers.join(",") + ",").indexOf("," + a.renderer + ",") < 0) {
            caviFail("Renderer " + a.renderer + " is not one of " + renderers.join(", "));
        }
        comp.renderer = a.renderer;
    }
    if (a.motion_blur !== null) { comp.motionBlur = a.motion_blur; }
    if (a.frame_blending !== null) { comp.frameBlending = a.frame_blending; }
    caviReport({comp: comp.name, source: source.name, duplicated: a.duplicate_as !== null, width: comp.width,
        height: comp.height, duration: comp.duration, fps: comp.frameRate, work_area_start: comp.workAreaStart,
        work_area_duration: comp.workAreaDuration, background: comp.bgColor, renderer: comp.renderer,
        motion_blur: comp.motionBlur, frame_blending: comp.frameBlending, errors: []});
})();
