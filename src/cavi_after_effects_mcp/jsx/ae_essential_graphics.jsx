$.evalFile(new File(CAVI_LIB));

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), i, spec, layer, prop, added = [], controls = [];
    if (a.template_name !== null) { comp.motionGraphicsTemplateName = a.template_name; }
    for (i = 0; i < a.add.length; i++) {
        spec = a.add[i];
        layer = caviLayer(comp, spec.layer);
        if (spec.property === null) {
            if (!(layer instanceof AVLayer) || !layer.canAddToMotionGraphicsTemplate(comp)) {
                caviFail("Layer " + layer.name + " cannot be a media replacement control: footage and comp layers "
                    + "with video can, once each");
            }
            layer.addToMotionGraphicsTemplateAs(comp, spec.name);
            added.push(spec.name);
            continue;
        }
        prop = caviProp(layer, spec.property);
        if (!prop.canAddToMotionGraphicsTemplate(comp)) {
            caviFail(spec.property + " cannot be added to Essential Graphics");
        }
        prop.addToMotionGraphicsTemplateAs(comp, spec.name);
        added.push(spec.name);
    }
    for (i = 1; i <= comp.motionGraphicsTemplateControllerCount; i++) {
        controls.push(comp.getMotionGraphicsTemplateControllerName(i));
    }
    caviReport({comp: comp.name, name: comp.motionGraphicsTemplateName, added: added, controls: controls, errors: []});
})();
