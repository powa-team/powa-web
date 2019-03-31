define([], function(){
    return {
      add_message: function(level, message) {
        $("#messages").append('<div class="alert-box ' + level + '">'
          + '<ul><li>' + message + '</li></ul>'
          + '<a href="#" class="close">&times;</a>'
          + '</div>');
        $(document).foundation();
        $(document).foundation('alert', 'reflow');
      }
    }
});
