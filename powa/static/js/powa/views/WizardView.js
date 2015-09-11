define([
        'powa/views/WidgetView',
        'powa/models/Wizard',
        'tpl!powa/templates/wizard.html',
        'highlight',
        'moment',
        'backgrid',
        'backbone'],
function(WidgetView, Wizard, template, highlight, moment, d3, Backgrid, Backbone){


    var h = "500",
        w = "200"; // Default width, then overriden by what the dashboard layout set.

    return WidgetView.extend({
        model: Wizard,
        template: template,

        initialize: function(args){
            this.model = args.model;
            this.listenTo(this.model, "widget:dataload-failed", this.fail);
            this.listenTo(this.model, "widget:update_progress", this.change_progress);
            this.listenTo(this.model, "wizard:solved", this.display_solution);
            this.$el.addClass("wizard-widget");
            this.render();
        },



        change_progress: function(state, progress){
            this.$progress_label.text(state);
            this.$progress_elem.css({width: progress + "%"});
        },

        showload: function(){

        },

        render: function(){
            var self = this;
            this.$el.html(this.template(this.model.toJSON()));
            this.$progress_elem = this.$el.find(".progress");
            this.$progress_label = this.$el.find(".progress_label");
            return this;
        },



        resolve_indexes: function(path){
            var self = this;
            this.change_progress("Collecting index suggestion", 0);
            var interesting_links = _.filter(path, function(link){
                return link.value != 0;
            });
            _.each(interesting_links , function(link, index){
                self.change_progress("Collecting index suggestion", index / interesting_links.length);
            });
        },

        display_solution: function(solutions){
            var grid = new Backgrid.Grid({
                columns: [
                {
                    editable: false,
                    name: "Indexes",
                    cell: "query"
                }, {
                    editable: false,
                    name: "Queries",
                    cell: "query",
                }, {
                    editable: false,
                    name: "Quals",
                    cell: "query"
                }],
                collection: new Backbone.Collection(_.values(solutions.by_index))
            });
            this.$gridel = this.$el.find(".indexes_grid");
            this.$gridel.append(grid.render().el);
        }

    });
});
