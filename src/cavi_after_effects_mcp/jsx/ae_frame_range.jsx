$.evalFile(new File(CAVI_LIB));

function pad(n) {
    var s = String(n);
    while (s.length < 5) { s = "0" + s; }
    return s;
}

// Writes frame_00001.png ... with Comp.saveFrameToPng from `start`, every `step` frames, for `duration` seconds.
(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), rate = comp.frameDuration, total, count, i, backdrop = null, files = [];
    var span = a.duration === null ? comp.duration - a.start : a.duration;
    if (a.start >= comp.duration) { caviFail("Start " + a.start + " s is past the comp duration " + comp.duration); }
    if (a.start + span > comp.duration + rate / 2) { caviFail("The range ends past the comp duration " + comp.duration); }
    total = Math.round(span / rate);
    count = Math.floor((total - 1) / a.step) + 1;
    if (count < 1) { caviFail("The range holds no frames"); }
    if (a.frames !== null) {
        if (a.frames > count) { caviFail("The range holds " + count + " frames, fewer than the " + a.frames + " asked for"); }
        count = a.frames;
    }
    if (count > a.max_frames) { caviFail("The range holds " + count + " frames; the limit is " + a.max_frames); }
    if (caviWarmCineware(comp, a.start, a.warm)) {
        caviReport({comp: comp.name, fps: comp.frameRate, step: a.step, count: count, warming: true, errors: []});
        return;
    }
    if (a.background) { backdrop = caviBackdrop(comp); }
    for (i = 0; i < count; i++) {
        files.push(a.directory + "/frame_" + pad(i + 1) + ".png");
        comp.saveFrameToPng(a.start + i * a.step * rate, new File(files[i]));
    }
    if (backdrop) { caviDropBackdrop(backdrop); }
    caviReport({comp: comp.name, fps: comp.frameRate, step: a.step, count: count, errors: []});
})();
