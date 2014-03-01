/**********
* User Interface function for Trac Custom Field Admin plugin.
* License: BSD
* (c) 2007-2009 ::: www.Optaros.com (cbalan@optaros.com)
**********/
(function($){
    function toggle_options(type_element){
        function label(property){
            return form.find(property).closest('div.field');
        }
        var form = $('#tabcontent');
        var value = type_element.options[type_element.selectedIndex].value;
        var show_fields;
        switch (value) {
            case 'text':
                show_fields = label('#format');
                break;
            case 'select':
                show_fields = label('#options');
                break;
            case 'checkbox':
                break;
            case 'radio':
                show_fields = label('#options');
                break;
            case 'textarea':
                show_fields = label('#cols, #rows, #format');
                break;
            default:
                show_fields = label('.field_' + value);
                break;
        }
        var hide_fields = $('div.field');
        hide_fields = hide_fields.not(label('[name=name], [name=type], ' +
                                            '[name=label], [name=value]'));
        if (show_fields)
            hide_fields = hide_fields.not(show_fields)
        hide_fields.hide();
        if (show_fields)
            show_fields.show();
    }

    $(document).ready(function(){
        $('#type').each(function(){
            toggle_options(this);
            $(this).change(function(){
                toggle_options(this);
            });
        });
    });
})(jQuery);
