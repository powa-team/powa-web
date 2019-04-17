define([], function(){
    return {
      add_message: function(level, message) {
        $("#messages").append('<div class="alert-box ' + level + '">'
          + '<ul><li>' + message + '</li></ul>'
          + '<a href="#" class="close">&times;</a>'
          + '</div>');
        $(document).foundation();
        $(document).foundation('alert', 'reflow');
      },

      format_change: function(change) {
        if (change["kind"] == "global") {
          data = change["data"];
          none = '<i class="fi-prohibited"></i>';

          txt = '<i class="fi-info"></i> <b><u>'
            + data["name"] + '</u></b> changed:<br />'
            + '<b>' + ((data["prev_is_dropped"]) ? none : data["prev_val"]) + '</b>'
            + ' to '
            + '<b>' + ((data["is_dropped"]) ? none : data["new_val"]) + '</b>'

          return txt;
        } else if (change["kind"] == "rds") {
          data = change["data"];
          none = '<i class="fi-prohibited"></i>';

          db = '';
          if (data["datname"])
            db = '<br />on database <b>' + data["datname"] + '</b>';

          role = '';
          if (data["setrole"] != 0)
            role = '<br />for role <b>' + data["setrole"] + '</b>';

          txt = '<i class="fi-info"></i> <b><u>'
            + data["name"] + '</u></b> changed:<br />'
            + '<b>' + ((data["prev_is_dropped"]) ? none : data["prev_val"]) + '</b>'
            + ' to '
            + '<b>' + ((data["is_dropped"]) ? none : data["new_val"]) + '</b>'
            + db
            + role

          return txt;
        } else if (change["kind"] == "reboot") {
          return '<i class="fi-alert"></i>'
            + '<b>Instance restarted!</b>';
        } else {
          return '<i class="fi-alert"></i> Unknown event "'
            + change["kind"]+ '":<br />'
            + change["data"];
        }
      }
    }
});
