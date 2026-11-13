$.evalFile(new File(CAVI_LIB));


function current(p) {
    var depth = {}, display = {}, count = {}, gpu = {};
    display[TimeDisplayType.FRAMES] = "frames"; display[TimeDisplayType.TIMECODE] = "timecode";
    count[FramesCountType.FC_START_0] = "start_0"; count[FramesCountType.FC_START_1] = "start_1";
    count[FramesCountType.FC_TIMECODE_CONVERSION] = "timecode_conversion";
    gpu[GpuAccelType.METAL] = "metal"; gpu[GpuAccelType.SOFTWARE] = "software";
    gpu[GpuAccelType.CUDA] = "cuda"; gpu[GpuAccelType.OPENCL] = "opencl";
    gpu[GpuAccelType.DIRECTX] = "directx"; gpu[GpuAccelType.VULKAN] = "vulkan";
    return {bits_per_channel: p.bitsPerChannel, linear_blending: p.linearBlending, working_space: p.workingSpace,
        display_start_frame: p.displayStartFrame, time_display: display[p.timeDisplayType],
        frames_count: count[p.framesCountType], expression_engine: p.expressionEngine, gpu: gpu[p.gpuAccelType]};
}

(function () {
    var a = CAVI_ARGS, p = app.project, i, found = false, profiles, display, count, gpu;
    display = {FRAMES: TimeDisplayType.FRAMES, TIMECODE: TimeDisplayType.TIMECODE};
    count = {START_0: FramesCountType.FC_START_0, START_1: FramesCountType.FC_START_1,
        TIMECODE_CONVERSION: FramesCountType.FC_TIMECODE_CONVERSION};
    gpu = {METAL: GpuAccelType.METAL, SOFTWARE: GpuAccelType.SOFTWARE};
    if (a.working_space !== null) {
        profiles = p.listColorProfiles();
        for (i = 0; i < profiles.length; i++) { if (profiles[i] === a.working_space) { found = true; } }
        if (!found && a.working_space !== "None") {
            caviFail("Unknown working space " + a.working_space + "; After Effects would silently set None");
        }
    }
    if (a.bits_per_channel !== null) { p.bitsPerChannel = a.bits_per_channel; }
    if (a.working_space !== null) { p.workingSpace = a.working_space; }
    if (a.linear_blending !== null) { p.linearBlending = a.linear_blending; }
    if (a.display_start_frame !== null) { p.displayStartFrame = a.display_start_frame; }
    if (a.time_display !== null) { p.timeDisplayType = caviEnum(display, a.time_display, "time display"); }
    if (a.frames_count !== null) { p.framesCountType = caviEnum(count, a.frames_count, "frames count"); }
    if (a.expression_engine !== null) { p.expressionEngine = a.expression_engine; }
    if (a.gpu !== null) { p.gpuAccelType = caviEnum(gpu, a.gpu, "GPU acceleration type"); }
    caviReport({settings: current(p), errors: []});
})();
