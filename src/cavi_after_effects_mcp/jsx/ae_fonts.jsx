$.evalFile(new File(CAVI_LIB));

(function () {
    var a = CAVI_ARGS, all = app.fonts.allFonts, found = [], i, j, font, line, needle = a.filter.toLowerCase();
    for (i = 0; i < all.length; i++) {
        for (j = 0; j < all[i].length; j++) {
            font = all[i][j];
            line = font.postScriptName + " " + font.familyName + " " + font.styleName;
            if (line.toLowerCase().indexOf(needle) >= 0) {
                found.push({postscript: font.postScriptName, family: font.familyName, style: font.styleName});
            }
        }
    }
    caviReport({fonts: found.slice(0, a.limit), count: found.length, errors: []});
})();
