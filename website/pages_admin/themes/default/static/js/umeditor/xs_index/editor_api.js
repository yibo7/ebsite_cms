/**
 * 开发版本的文件导入-  CQS修改远程调用
 */
(function (){
    var paths  = [
            'editor.js',
            'core/browser.js',
            'core/utils.js',
            'core/EventBase.js',
            'core/dtd.js',
            'core/domUtils.js',
            'core/Range.js',
            'core/Selection.js',
            'core/Editor.js',
            'core/filterword.js',
            'core/node.js',
            'core/htmlparser.js',
            'core/filternode.js',
            'plugins/inserthtml.js',
            'plugins/image.js',
            'plugins/justify.js',
            'plugins/font.js',
            'plugins/link.js',
            'plugins/print.js',
            'plugins/paragraph.js',
            'plugins/horizontal.js',
            'plugins/cleardoc.js',
            'plugins/undo.js',
            'plugins/paste.js',
            'plugins/list.js',
            'plugins/source.js',
            'plugins/enterkey.js',
            'plugins/preview.js',
            'plugins/basestyle.js',
            'plugins/video.js',
            'plugins/selectall.js',
            'plugins/removeformat.js',
            'plugins/keystrokes.js',
            'plugins/autosave.js',
            'plugins/autoupload.js',
            'plugins/formula.js',
            'plugins/xssFilter.js',
            'ui/widget.js',
            'ui/button.js',
            'ui/toolbar.js',
            'ui/menu.js',
            'ui/dropmenu.js',
            'ui/splitbutton.js',
            'ui/colorsplitbutton.js',
            'ui/popup.js',
            'ui/scale.js',
            'ui/colorpicker.js',
            'ui/combobox.js',
            'ui/buttoncombobox.js',
            'ui/modal.js',
            'ui/tooltip.js',
            'ui/tab.js',
            'ui/separator.js',
            'ui/scale.js',
            'adapter/adapter.js',
            'adapter/button.js',
            'adapter/fullscreen.js',
            'adapter/dialog.js',
            'adapter/popup.js',
            'adapter/imagescale.js',
            'adapter/autofloat.js',
            'adapter/source.js',
            'adapter/combobox.js'
        ],
    baseURL = 'https://cdn.jsdelivr.net/gh/yibo7/ebcdn@0.6/umeditor/_src/';
    for (var i=0,pi;pi = paths[i++];) {
        document.write('<script type="text/javascript" src="'+ baseURL + pi +'"></script>');
    }
})();
