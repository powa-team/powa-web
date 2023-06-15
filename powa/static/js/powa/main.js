
require(['jquery',
  'foundation/foundation',
  'underscore',
  'backbone',
  'powa/views/DashboardView',
  'powa/models/Widget',
  'powa/models/Dashboard',
  'powa/models/DataSourceCollection',
  'powa/models/MetricGroup',
  'powa/models/ContentSource',
  'powa/utils/timeurls',
  'powa/utils/message',
  'highlight',
  'popper',
  'tippy',
  'powa/views/LineGraphView',
  'powa/views/BarGraphView',
  'powa/views/PieGraphView',
  'powa/views/GridView',
  'powa/views/ContentView',
  'powa/views/WizardView',
  'powa/models/Graph',
  'powa/models/Grid',
  'powa/models/Content',
  'powa/models/Wizard',
  'powa/models/TabContainer',
  'modernizr',
  'foundation/foundation.tab',
  'foundation/foundation.tooltip',
  'foundation/foundation.dropdown',
  'foundation/foundation.topbar',
  'foundation/foundation.alert'],
  function($, Foundation, _, BackBone, DashboardView,
    Widget,
    Dashboard,
    DataSourceCollection,
    MetricGroup,
    ContentSource,
    timeurls,
    Message,
    highlight,
    popper,
    tippy) {

    $(function(){

      var colors = ["#c05020", "#30c020", "#6060c0"];
      var ds = DataSourceCollection.get_instance();
      var picker = new timeurls({$el: $('#daterangepicker')});
      var dashboards = [];

      $('script[type="text/datasources"]').each(function(){
        var metric_groups = JSON.parse($(this).text());
        $.each(metric_groups, function(){
          try{
            if(this.type == "metric_group"){
              ds.add(MetricGroup.fromJSON(this));
            } else if (this.type == "content") {
              ds.add(ContentSource.fromJSON(this));
            }
          }
          catch(e){
            console.error("Could not instantiate metric group. Check the metric group definition");
          }

        });
      });

      $('.dashboard').each(function(){
        var widgets = new Backbone.Collection();
        var self = this;
        $(this).find('script[type="text/dashboard"]').each(function(){
          var dashboard = Widget.fromJSON(JSON.parse(this.text));
          var dashboardview = dashboard.makeView({el: $(self).find('.widgets')});
          dashboards.push(dashboard);
          dashboardview.listenTo(picker, "pickerChanged", dashboardview.refreshSources, dashboardview);
          dashboardview.refreshSources(picker.start_date, picker.end_date);
          picker.listenTo(dashboardview, "dashboard:updatePeriod", picker.updateUrls, picker);
        });
      });

      $("#reload_collector").click(function() {
        $.ajax({
          url: '/reload_collector/',
          type: 'GET',
        }).done(function(response) {
          if (response)
            Message.add_message("success", "Collector successfully reloaded!");
          else
            Message.add_message("alert", "Could not reload collector.");
        }).fail(function(response) {
          Message.add_message("alert", "Error while trying to reload the collector.");
        });
      });

      $("#force_snapshot").click(function() {
        var srvid = this.dataset.srvid

        $.ajax({
          url: '/force_snapshot/' + srvid,
          type: 'GET',
        }).done(function(response) {
          if (response)
          {
            console.log(response);
            $.each(response, function(i) {
              var json = response[i];
              var k = Object.keys(json)[0];
              var v = json[k]
              var level;
              var msg;

              switch(k) {
                case 'OK':
                  level = 'success';
                  msg = "Forced snapshot requested. Status:"
                  break;
                case 'WARNING':
                case 'UNKNOWN':
                  level = 'warning';
                  msg = "Problem with forcing an immediate snapshot:"
                  break;
                default:
                  level = 'alert';
                  msg = "Could not force an immediate snapshot:"
                  break;
              }

              msg += "<br/>" + v;

              Message.add_message(level, msg);
            });
          }
          else
            Message.add_message("alert", "Could not force an immediate snapshot.");
        }).fail(function(response) {
          Message.add_message("alert", "Error while trying to force an immediate snapshot.");
        });
      });

      $("#refresh_db_cat").click(function() {
        var srvid = this.dataset.srvid
        var dbnames = []

        if ('dbname' in this.dataset) {
          dbnames.push(this.dataset.dbname);
        }

        $.ajax({
          url: '/refresh_db_cat/',
          type: 'POST',
          data: JSON.stringify({'srvid': srvid, 'dbnames': dbnames}),
          contentType: "application/json; charset=utf-8",
          datatype: 'json',
        }).done(function(response) {
          if (response)
          {
            console.log(response);
            $.each(response, function(i) {
              var json = response[i];
              var k = Object.keys(json)[0];
              var v = json[k]
              var level;
              var msg;

              switch(k) {
                case 'OK':
                  level = 'success';
                  msg = "Catalog refresh successfully registered:"
                  break;
                case 'WARNING':
                case 'UNKNOWN':
                  level = 'warning';
                  msg = "Problem with registering the catalog refresh:"
                  break;
                default:
                  level = 'alert';
                  msg = "Could not register the catalog refresh:"
                  break;
              }

              msg += "<br/>" + v;

              Message.add_message(level, msg);
            });
          }
          else
            Message.add_message("alert", "Could not refresh the catalogs.");
        }).fail(function(response) {
          Message.add_message("alert", "Error while trying to refresh the catalogs.");
        });
      });

      // ensure that dropdown are taken into account
      $(document).foundation();
    });
    return {};
  });
