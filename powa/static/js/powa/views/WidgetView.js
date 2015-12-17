define([
        'backbone',
        'spin'
    ], function(backbone, Spinner){
    var registry = {};
    var makeInstance = function(options){
        return new this(options);
    };

    return Backbone.View.extend({

        spinner_opts : {

        },

        showload: function(){
            this.loading = true;
            if(this.spinner === undefined){
                this.spinner = new Spinner(this.spinner_opts);
            }
            this.spinner.spin(this.el);
        },

        fail: function(message){
            this.hideload();
            this.$el.html('<div class="alert-box info">An error occured while loading this widget <br/>' +
                    message + '</div>');
        },

        hideload: function(){
            if(this.spinner){
                this.spinner.stop();
            }
        },

        updatePeriod: function(startDate, endDate){
            this.from_date = startDate
            this.to_date = endDate;
            this.showload();
        },

        zoomIn: function(startDate, endDate){
            this.showload();
        },

        show: function(){

        }


    }, {
        extend: function(instanceattrs, clsattrs){
            var newcls = Backbone.View.extend.apply(this, [instanceattrs, clsattrs]);
            registry[newcls.prototype.typname] = newcls;
            if(!newcls.makeInstance){
                newcls.makeInstance = makeInstance;
            }
            return newcls;
        },
        makeView: function(model){
            return registry[model.typname].makeInstance({model: model});
        }
    });
});

