define(['backbone', 'powa/models/DataSourceCollection', 'jquery',
        'powa/views/GridView', 'highlight'], function(Backbone, DataSourceCollection, $){

    var QualCollection = Backbone.Collection.extend({
        comparator: function (qual1, qual2){
            if(qual1.get("relid") != qual2.get("relid")){
                return qual1.get("relid") - qual2.get("relid")
            }
            if(qual1.get("attnum") != qual2.get("attnum")){
                return qual1.get("attnum") - qual2.get("attnum");
            }
            if(qual1.get("opno") != qual2.get("opno")){
                return qual1.get("opno") - qual2.get("opno");
            }
            return 0;
        }
    });

    var make_attrid = function(qual){
        return "" + qual.get("relid") + "/" + qual.get("attnum");
    }

    return Backbone.Model.extend({
        initialize: function(){
            this.set("stage", "Starting wizard...");
            this.set("progress", 0);
            this.startNode = { label: "Start", type: "startNode", quals: new QualCollection(), links: {}, id: "start",
                               x: 0.5, y: 0.5 };
            this.set("nodes", [this.startNode]);
            this.set("links", []);
            this.set("shortest_path", []);
            this.listenTo(this.get("datasource"), "metricgroup:dataload", this.update, this);
            this.listenTo(this.get("datasource"), "startload", this.starload, this);
            this.set("cache", {});
        },

        startload: function(){
            this.trigger("widget:update_progress", "Fetching top 20 quals...", 0);
        },

        /* Compute the links between quals.
         *
         * Two types of links are considered:
         *  - Almost-free links, where two predicates can be grouped together
         *  using a single index
         *  - Expensive links, where a new index has to be created.
         *
         * */
        computeLinks: function(nodes){
            var nodesToTrash = [];
            for(var i=0; i <nodes.length; i++){
                var firstnode = nodes[i];
                for(var j=0; j<i; j++){
                    var secondnode = nodes[j];
                    nodesToTrash = nodesToTrash.concat(this.make_links(firstnode, secondnode));
                }
            }
            _.each(nodes, function(nodesource){
                nodesource.contained = _.difference(nodesource.contained, nodesToTrash);
            });
            return _.difference(nodes, nodesToTrash);
        },

        make_links: function (node1, node2) {
            // This functions assumes that qual1.quals and qual2.quals are sorted
            // according to the (relid,attnum,opno) tuple.
            // This is basically a merge-join.
            var idx1 = 0, idx2 = 0, l1 = node1.quals.models, l2 = node2.quals.models;
            var overlap = [];
            var attrs1 = {}, attrs2 = {};
            var relid1, relid2;
            var links = [];
            var missing1 = [], missing2 = [];
            l1 = new QualCollection(_.uniq(l1, false, function(q){ return [q.get("attnum"), q.get("relid")].join(".")})).models;
            l2 = new QualCollection(_.uniq(l2, false, function(q){ return [q.get("attnum"), q.get("relid")].join(".")})).models;
            while(true){
                if(idx1 >= l1.length || idx2 >= l2.length){
                    for(var i = idx1; i < l1.length; i++){
                        missing1.push(l1[i]);
                    }
                    for(var i = idx2; i < l2.length; i++){
                        missing2.push(l2[i]);
                    }
                    break;
                }
                var q1 = l1[idx1],
                    q2 = l2[idx2],
                    attrid1 = make_attrid(q1),
                    attrid2 = make_attrid(q2);
                if(attrs1[attrid1] === undefined){
                    attrs1[attrid1] = false;
                }
                if(attrs2[attrid2] === undefined){
                    attrs2[attrid2] = false;
                }
                if(relid1 && relid1 != q1.get("relid")){
                    throw "A single qual should NOT touch more than one table!";
                }
                relid1 = q1.get("relid");
                if(relid2 && relid2 != q2.get("relid")){
                    throw "A single qual should NOT touch more than one table!";
                }
                relid2 = q2.get("relid");
                if(q1.get("relid") == q2.get("relid") &&
                q1.get("attnum") == q2.get("attnum")){
                    var common_ams = _.filter(_.keys(q1.get("amops")), function(indexam){
                        return q2.get("amops")[indexam] != undefined;
                    });
                    if(common_ams.length > 0){
                        overlap.push({
                            relid: q1.get("relid"),
                            queryids: [q1.get("queryid"), q2.get("queryid")],
                            attnum: q1.get("attnum"),
                            relname: q1.get("relname"),
                            attname: q1.get("attname"),
                            indexams: common_ams,
                            q1_idx: idx1,
                            q2_idx: idx2
                        });
                        attrs1[attrid1] = true;
                        attrs2[attrid2] = true;
                    }
                    idx1++;
                    idx2++;
                    continue;
                } else {
                    if(node1.quals.comparator.call(q1, q1, q2) > 0){
                        var newq2 = _.clone(q2);
                        newq2.qualid = node2.qualid;
                        missing2.push(newq2);
                        idx2++;
                    } else {
                        var newq1 = _.clone(q1);
                        newq1.qualid = node1.qualid;
                        missing1.push(newq1);
                        idx1++;
                    }
                }
            }
            var samerel = relid1 != undefined && relid2 != undefined && relid1 == relid2;
            overlap = _.uniq(overlap, function(item){
                return item.attnum;
            });

            node1.relid = relid1;
            node2.relid = relid2;
            if(missing1.length == 0 && missing2.length == 0){
                node1.queries = node1.queries.concat(node2.queries);
                node1.qualstrs = node1.queries.concat(node2.qualstrs);
                return [node2];
            }
            if(missing2.length == 0){
                node1.contained.push(node2);
            }
            if(missing1.length == 0){
                node2.contained.push(node1);
            }
            return [];
        },

        update: function(quals, from_date, to_date){
            var total_quals = _.size(quals);
            if (total_quals == 0){
                this.trigger("widget:update_progress", "No qual found!", 100);
                return;
            }
            var nodes = [];
            _.each(quals, function(qual, index){
                var node = {
                    label: qual.where_clause,
                    type: "qual",
                    quals: new QualCollection(_.filter(qual.quals, function(qual){return _.keys(qual.amops).length > 0})),
                    from_date: from_date,
                    to_date: to_date,
                    queries: qual.queries,
                    qualstrs: [qual.where_clause],
                    links: {},
                    id: qual.qualid,
                    contained: []
                }
                node.attnums = _.uniq(_.map(node.quals.models, function(qual){ return qual.attributes.attnum }));
                node.score = node.attnums.length;
                nodes.push(node);
            }, this);
            nodes = this.computeLinks(nodes);
            this.solve(nodes);
        },


        findContained: function(node1, nodes){
            var contained = [];
            _.each(nodes, function(node) {
                var link = node1.links[node.id];
                if(link != undefined && link.missing.length == 0){
                    contained.push(node);
                }
            });
            return contained;
        },

        solve: function(nodes){
            var remainingNodes = _.clone(nodes);
            var pathes = {};

            var makePathId = function(nodes){
                return _.pluck(nodes, "id").join(",");
            };
            var getPathes = function(node){
                var mypath = {
                    id: node.id,
                    score: node.score,
                    nodes: [node]
                };
                var pathes = [];
                _.each(node.contained, function(contained){
                    var child_pathes = getPathes(contained);
                    _.each(child_pathes, function(path){
                        var current_path = _.clone(path.nodes);
                        current_path.push(node);
                        pathes.push({
                            nodes: current_path,
                            id: makePathId(current_path),
                            score: node.score + path.score
                        });
                    });
                }, this);
                pathes.push(mypath);
                return pathes;
            };

            _.each(remainingNodes, function(node){
                _.each(getPathes(node), function(path){
                    pathes[path.id] = path;
                });
            });
            console.log(pathes);
            var indexes = [];
            var safeguard = 0;
            while(_.values(pathes).length > 0 && safeguard < 1000){
                safeguard++;
                /* Work with the remainging highest-scoring path */
                var firstPath = _.max(_.pairs(pathes), function(pair){
                    return pair[1].score;
                })[1];
                var root = firstPath.nodes.slice(-1)[0];
                _.each(_.keys(pathes), function(key){
                    if(key.endsWith(root.id)){
                        delete pathes[key];
                    }
                });
                /* Find attnum order */
                var attnums = [];
                var queryids = [];
                var qualstrs = [];
                _.each(firstPath.nodes, function(node, idx){
                    var newAttnums = _.difference(node.attnums, attnums);
                    var idToDel = makePathId(firstPath.nodes.slice(0, idx+1));
                    attnums = attnums.concat(newAttnums);
                    _.each(_.pairs(pathes), function(pair){
                        var pathid = pair[0];
                        var path = pair[1];
                        if(path.nodes.indexOf(node) > -1){
                            var pathToDel = pathes[pathid];
                            delete pathes[pathid];
                        }
                    });
                    delete pathes[idToDel];
                    queryids = queryids.concat(node.queryids);
                    qualstrs = qualstrs.concat(node.qualstrs);
                });
                indexes.push({
                    relid: firstPath.nodes[0].relid,
                    attnums: attnums,
                    queryids: queryids,
                    qualstrs: qualstrs
                });
            }
            console.log("INDEXES: ", indexes);
        }

    }, {
        fromJSON: function(jsonobj){
            var group = DataSourceCollection.get_instance();
            jsonobj.datasource = group.findWhere({name: jsonobj.datasource});
            if(jsonobj.datasource === undefined){
                throw ("The content source could not be found.");
            }
            return new this(jsonobj);
        }
    });
});
