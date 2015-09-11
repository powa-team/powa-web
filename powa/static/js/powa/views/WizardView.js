define([
        'powa/views/WidgetView',
        'powa/models/Wizard',
        'tpl!powa/templates/wizard.html',
        'highlight',
        'moment',
        'backgrid',
        'backbone'],
function(WidgetView, Wizard, template, highlight, moment, Backgrid, Backbone){


    var h = "500",
        w = "200"; // Default width, then overriden by what the dashboard layout set.

    return WidgetView.extend({
        model: Wizard,
        template: template,

        events: {
            "click .launcher": "launchOptimization"
        },

        initialize: function(args){
            this.model = args.model;
            this.listenTo(this.model, "widget:dataload-failed", this.fail);
            this.listenTo(this.model, "widget:update_progress", this.change_progress);
            this.listenTo(this.model, "wizard:start", this.onStart);
            this.listenTo(this.model, "wizard:end", this.onEnd);
            this.$el.addClass("wizard-widget");
            this.indexgrid = new Backgrid.Grid({
                columns: [{
                    editable: false,
                    name: "ddl",
                    label: "Index",
                    cell: "query"
                },{
                    editable: false,
                    name: "quals",
                    label: "Used by",
                    cell: "html",
                }],
                collection: this.model.get("indexes")
            });
            this.render();
        },



        change_progress: function(state, progress){
            this.$progress_label.text(state);
            this.$progress_elem.css({width: progress + "%"});
        },

        onStart: function(state, progress){
            this.$el.find(".configuration").hide();
            this.$el.find(".summary").show();
        },

        onEnd: function(state, progress){
            this.$el.find(".configuration").show();
        },

        showload: function(){

        },

        render: function(){
            var self = this;
            if(!this.model.get("has_qualstats")){
                this.$el.html('<h4>' + this.model.get("title") + '</h4>' +
                        '<span>Impossible to suggest indexes: please ' +
                        ' enable support for pg_qualstats in powa ' +
                        ' See <a href="http://powa.readthedocs.org"> ' +
                        ' the documentation for more information</span>');
                return this;
            }
            this.$el.html(this.template(this.model.toJSON()));
            this.$el.find(".summary").hide();
            this.$el.find(".results").hide();
            this.$el.find(".results").hide();
            this.$progress_elem = this.$el.find(".progress");
            this.$progress_label = this.$el.find(".progress_label");
            this.$gridel = this.$el.find(".indexesgrid");
            this.$gridel.append(this.indexgrid.render().el);
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

        launchOptimization: function(){
            this.model.launchOptimization({
                from_date: this.from_date,
                to_date: this.to_date
            });
        },

        updateIndexList: function(){
        }

    });
});
