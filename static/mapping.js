
// Global Variables
var map = null;
var marker = null;
var current_user_vector = null;
var venue_list = new Array();
var rejected_locations = new Array();
var current_path = null;
var active_chain = false;
var _lastIndex = 0;
var clickable = false;
var word_bubbles = new bubble_plot("#vis", 700, 300);
var choices = new Array();

//var alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
//var marker_colors = ["blue", "brown", "darkgreen", "orange", "paleblue", "pink",
//		     "purple", "red", "yellow"];
//var marker_colors = ["white", "yellow", "red", "purple", "orange", "green", "gray", "brown", "blue", "black"]


var marker_colors = [/*'FFFFFF', 'FFFF00', 'FFCC33',*/ 'FF9966', 'FF6699', 'FF33CC', 'FF00FF', 'FF0000', 
		     'CCFF33', 'CCCC66', 'CC9999', 'CC66CC', 'CC33FF', 'CC3300', 'CC0033', '99FF66', 
		     '99CC99', '9999CC', '9966FF', '996600', '993333', '990066', '66FF99', '66CCCC', 
		     '6699FF', '669900', '666633', '663366', '660099', '33FFCC', '33CCFF', '33CC00', 
		     '339933', '336666', '333399', '3300CC', '00FFFF', '00FF00', '00CC33', '009966', 
		     '006699', '0033CC', '0000FF', '000000']

var marker_colors = [/*'66FF99', 'FF0000', '33CCFF', '666633',*/ 'CC3300', 'FFCC33', /*'CC0033',*/ 'FF33CC', 
		     '00FFFF', 'FFFFFF', '990066', '006699', '33FFCC', '99FF66', '336666', 
		     'CC66CC', 'FF6699', '00CC33', '996600', 'FF00FF', '9999CC', '663366', '6699FF', 
		     '993333', '99CC99', '0000FF', 'CCFF33', 'FF9966', '66CCCC', '3300CC', '0033CC', 
		     '33CC00', 'FFFF00', '339933', '00FF00', '669900', 'CC9999', 'CCCC66', '333399', 
		     '9966FF', 'CC33FF', '660099', '009966']


/*

var marker_colors = ['#FFFFFF', '#FFFFCC', '#FFFF99', '#FFFF66', '#FFFF33', '#FFFF00', '#FFCCFF', '#FFCCCC', 
		     '#FFCC99', '#FFCC66', '#FFCC33', '#FFCC00', '#FF99FF', '#FF99CC', '#FF9999', '#FF9966', 
		     '#FF9933', '#FF9900', '#FF66FF', '#FF66CC', '#FF6699', '#FF6666', '#FF6633', '#FF6600', 
		     '#FF33FF', '#FF33CC', '#FF3399', '#FF3366', '#FF3333', '#FF3300', '#FF00FF', '#FF00CC', 
		     '#FF0099', '#FF0066', '#FF0033', '#FF0000', '#CCFFFF', '#CCFFCC', '#CCFF99', '#CCFF66', 
		     '#CCFF33', '#CCFF00', '#CCCCFF', '#CCCCCC', '#CCCC99', '#CCCC66', '#CCCC33', '#CCCC00', 
		     '#CC99FF', '#CC99CC', '#CC9999', '#CC9966', '#CC9933', '#CC9900', '#CC66FF', '#CC66CC', 
		     '#CC6699', '#CC6666', '#CC6633', '#CC6600', '#CC33FF', '#CC33CC', '#CC3399', '#CC3366', 
		     '#CC3333', '#CC3300', '#CC00FF', '#CC00CC', '#CC0099', '#CC0066', '#CC0033', '#CC0000', 
		     '#99FFFF', '#99FFCC', '#99FF99', '#99FF66', '#99FF33', '#99FF00', '#99CCFF', '#99CCCC', 
		     '#99CC99', '#99CC66', '#99CC33', '#99CC00', '#9999FF', '#9999CC', '#999999', '#999966', 
		     '#999933', '#999900', '#9966FF', '#9966CC', '#996699', '#996666', '#996633', '#996600', 
		     '#9933FF', '#9933CC', '#993399', '#993366', '#993333', '#993300', '#9900FF', '#9900CC', 
		     '#990099', '#990066', '#990033', '#990000', '#66FFFF', '#66FFCC', '#66FF99', '#66FF66', 
		     '#66FF33', '#66FF00', '#66CCFF', '#66CCCC', '#66CC99', '#66CC66', '#66CC33', '#66CC00', 
		     '#6699FF', '#6699CC', '#669999', '#669966', '#669933', '#669900', '#6666FF', '#6666CC', 
		     '#666699', '#666666', '#666633', '#666600', '#6633FF', '#6633CC', '#663399', '#663366', 
		     '#663333', '#663300', '#6600FF', '#6600CC', '#660099', '#660066', '#660033', '#660000', 
		     '#33FFFF', '#33FFCC', '#33FF99', '#33FF66', '#33FF33', '#33FF00', '#33CCFF', '#33CCCC', 
		     '#33CC99', '#33CC66', '#33CC33', '#33CC00', '#3399FF', '#3399CC', '#339999', '#339966', '#339933', '#339900', '#3366FF', '#3366CC', '#336699', '#336666', '#336633', '#336600', '#3333FF', '#3333CC', '#333399', '#333366', '#333333', '#333300', '#3300FF', '#3300CC', '#330099', '#330066', '#330033', '#330000', '#00FFFF', '#00FFCC', '#00FF99', '#00FF66', '#00FF33', '#00FF00', '#00CCFF', '#00CCCC', '#00CC99', '#00CC66', '#00CC33', '#00CC00', '#0099FF', '#0099CC', '#009999', '#009966', '#009933', '#009900', '#0066FF', '#0066CC', '#006699', '#006666', '#006633', '#006600', '#0033FF', '#0033CC', '#003399', '#003366', '#003333', '#003300', '#0000FF', '#0000CC', '#000099', '#000066', '#000033', '#000000']
*/


function createMarker(idx) {
    // http://stackoverflow.com/questions/7095574/google-maps-api-3-custom-marker-color-for-default-dot-marker

    var pinColor = marker_colors[ idx % marker_colors.length];

    // var pinColor = "FE7569";
//    var pinImage = new google.maps.MarkerImage("http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=%E2%80%A2|" + pinColor,
    var pinImage = new google.maps.MarkerImage("/static/markers/marker_" + pinColor + ".png",
					       new google.maps.Size(21, 34),
					       new google.maps.Point(0,0),
					       new google.maps.Point(10, 34));

//    var pinShadow = new google.maps.MarkerImage("http://chart.apis.google.com/chart?chst=d_map_pin_shadow",
    var pinShadow = new google.maps.MarkerImage("/static/markers/map_pin_shadow.png",
						new google.maps.Size(40, 37),
						new google.maps.Point(0, 0),
						new google.maps.Point(12, 35));
    
    return [pinImage, pinShadow] //"/static/markers/" + color + ".png"; 
    
}


// Venue class
function venue(data) {

    var self = this;
    this.data = data;

    // Give this venue a unique index
    this.index = _lastIndex;
    _lastIndex += 1;

    // Create the lat/lon object
    var lat = data['latitude'];
    var lon = data['longitude'];
    this.latlon = new google.maps.LatLng(lat, lon);

    // Create the marker
    this.marker_image = createMarker(this.index)[0];
    this.marker_shadow = createMarker(this.index)[1];
    var marker = new google.maps.Marker({
	position: self.latlon,
	map: map,
	icon: this.marker_image,
	animation: google.maps.Animation.DROP
    });
    this.marker = marker;

    // To be filled later
    this.path = new Array(self.latlon);
    this.directions = null;
    this.table_row = null;

}


venue.prototype.clear = function() {

    // Remove the marker from the map
    this.marker.setMap(null);
    //$("#right_column").hide();
    // Remove the entry from the table    
    if( this.table_row != null ) {
	console.log("Removing table entry");
	this.table_row.remove();
    }
}


venue.prototype.add_path = function(last_point) {
    var self = this;
    var service = new google.maps.DirectionsService();
    service.route({
	origin: last_point,
	destination: self.latlon,
	travelMode: google.maps.DirectionsTravelMode.WALKING
    }, function(result, status) {
	if (status == google.maps.DirectionsStatus.OK) {
	    var new_path = result.routes[0].overview_path;
	    console.log("Found Path:");
	    console.log(result);
	    self.path = new_path;
	    updatePath();

	    // Get the directions
	    var steps = result.routes[0].legs[0].steps;
	    var directions = "";
	    for(var i=0; i<steps.length; ++i) {
		if( i != 0) {
		    directions += ", ";
		}
		directions += steps[i].instructions;
	    }
	    self.directions = directions;
	    return new_path;
	}
	else {
	    console.log("Add Path Error");
	}
    });
}

/*
venue.prototype.create_path = function(last_lat_long, callback) {

    var self = this;

    var service = new google.maps.DirectionsService();
    service.route({
	origin: last_lat_long,
	destination: self.latlon,
	travelMode: google.maps.DirectionsTravelMode.WALKING
    }, function(result, status) {
	if (status == google.maps.DirectionsStatus.OK) {
	    var new_path = result.routes[0].overview_path;
	    self.path = new_path;
	    callback();
	}
	else {
	    console.log("Create Path Error");
	}
    });
}
*/

venue.prototype.table_id = function() {
    if(this.table_row != null) {
	var button = $(this.table_row).find(".button_remove")[0];
	return button.id; //attr('id'); //.table_row.id()
    }
    else {
	return null;
    }
}


// Create a twitter bootstrap collapsable
// It consists of two parts:
//   - The button that toggles the collapse
//   - The data section
// The 'id' input is the idea of the entire block
// The 'title' is the name on the toggle button
// The 'content' is the data that gets shown and hidden
// This function returns an html string
function createCollapsable(id, title, content) {

    var html_string = ' \
	<div class="accordion" id="' + id + '"> \
	 <div class="accordion-group"> \
          <div class="accordion-heading"> \
	    <a class="accordion-toggle" data-toggle="collapse" \
               data-parent="#' + id + '" href="#collapse_' + id + '"> \
	      ' + title + ' \
	    </a> \
	  </div> \
	  <div id="collapse_' + id + '" class="accordion-body collapse" style="max-height: 200px" > \
	    <div class="accordion-inner" style="height: 200px; overflow: scroll;"> \
	      ' + content + ' \
	    </div> \
	  </div> \
	</div> \
      </div>';

    return html_string;

}


venue.prototype.add_to_table = function() {

    var table = $("#venue_list");
    
    var row_index = this.index;
    console.log("Creating row Object " + row_index);

    var data = this.data;
    console.log(data);

    var name = data['name'];
    var address = data['nymag']['address'];
    var category_list = data['nymag']['categories'];
    var tips_list = data['foursquare']['tips'];

    var Description = data['nymag']['review'];
    Description += '<br> <br> <ul>';
    for(var i=0; i < tips_list.length && i < 5; ++i) {
	Description += "<li>" + tips_list[i]['text'] + "</li>";
    }
    Description += '</ul>';

    var category_string = '';
    for(var i=0; i < category_list.length; ++i) {
	category_string += category_list[i];
	if(i != category_list.length-1) {
	    category_string += ", ";   
	}
    }

    var row_html_string = '<div class="venue_row_element row-fluid span12 well" id="row_' + row_index + '">\
\
<div class="span2"><img src="' + this.marker_image.url +'"> </div><div class="span4"><p><strong>' + name + '</strong></p> </div>\
<div class="span5" style="text-align: right;"> \
<button id="button_remove_' + row_index + '" class="button_remove btn btn-small btn-danger">Remove</button> </div> \
<div class="span6"> <p>' + address + '</p> </div> \
<div class="span12">' + category_string + '</div> \
<div class="span12 Description_container"> <div class="Description"> </div> </div>\
</div>';

    // Create the row from the html
    var tail_row = $(row_html_string);

    // Add the collapsable Description
    var collapsable = createCollapsable("row_" + row_index + "_Description", "Description", Description);
    tail_row.find(".Description").html(collapsable);

    table.append(tail_row);
    this.table_row = tail_row;
}


function removeVenueWithButtonId(button_id) {

    console.log("Removing using button id: " + button_id);
    
    for(var i=0; i < venue_list.length; ++i) {
	var this_id = venue_list[i].table_id();
	console.log("Row Id: " + this_id);
	if(venue_list[i].table_id() == button_id) {
	    console.log("Splicing!!!");
	    var venue = venue_list[i];
	    choice = {'venue' : venue.data, 'accepted' : false};
	    choices.push(choice);
	    rejected_locations.push(venue.data);
	    venue.clear();
	    venue_list.splice(i, 1);
	    updatePath();
	    break;
	}
    }
}


function beginChain(latlon) {

    // First, check if there is an existing
    // chain.  If so, we kill it.
    if(active_chain==true) {
	clearChain();
    }

    // Create a new path
    current_path = new google.maps.Polyline({
	strokeColor: "#0000FF",
	strokeOpacity: 0.8,
	strokeWeight: 4
    });
    current_path.setMap(map);

    // To be done by clicking
    //latlon = event.latLng;
    var data = {};
    data['latitude'] = latlon.lat();
    data['longitude'] = latlon.lng();
    data['initial'] = true;

    // Create the new object
    var initial_location = new venue(data);
    venue_list.push(initial_location);

    // Change the state
    active_chain = true;
    clickable = true;
    //$("#right_column").show();
    $("#button_accept").html("Find Venue");
    $("#buttons").show();
    $("#button_try_another").hide();
    $("#instruction_content").html("Enter another address or click the map to start a new chain");
    
    return;

}


// Update the shown path based on the current
// List of LatLon points
function updatePath() {
    var total_chain = new Array();
    for(var i=0; i < venue_list.length; ++i) {
	var path = venue_list[i].path;
	total_chain = total_chain.concat(path);
    }
    console.log("Total Chain:");
    console.log(total_chain);
    current_path.setPath(total_chain);
}


function addToChain(location_dict) {

    console.log("Adding new location:");
    console.log(location_dict);

    var last_lat_long = venue_list[venue_list.length - 1].latlon;

    // Create a new venue
    var next_venue = new venue(location_dict);
    venue_list.push(next_venue);

    // Add to the table
    next_venue.add_to_table();

    // Get the updated path between the last point
    // and the new point
    next_venue.add_path(last_lat_long);
    return;

    //var last_lat_long = venue_list[venue_list.length - 1].latlon;
    //next_venue.create_path(last_lat_long, updatePath);

    return;
}


function clearChain() {

    // Clear the array
    for(var i=0; i < venue_list.length; ++i) {
	venue_list[i].clear();
    }
    venue_list.length = 0;

    current_path.setMap(null);
    current_path = null;

    //$("#venue_list").hide();

    d3.select("#vis").select("svg")
	.remove();
    d3.select("#vis").select("#bubble-labels")
	.remove();

    active_chain = false;
    $("#buttons").hide();
    return;

}


// Get the next 'location' based on the current
// chain of locations
function getNextLocation(accepted) {

    $("#right_column").show();

    if(clickable == false) {
	console.log("Cannot Click Yet");
	return;
    }

    if(active_chain == false) {
	console.log("Cannot submit to server, chain isn't yet active");
	return;
    }

    if( venue_list.length == 0 ) {
	console.log("Error: No venues exist yet");
	return;
    }

    // If we only have the inital marker, we
    // must use a special api point
    if( venue_list.length == 1 ){
	var data = {'location' : venue_list[0].data}
	submitToServer('/api/initial_location', data);
    }
    
    // Otherwise, we get the next venue basee
    // on the current chain
    else {
	var chain = new Array();
	for( var i = 0; i < venue_list.length; ++i) {
	    chain.push(venue_list[i].data);
	}
	
	if( accepted ) {
	    choice = {'venue' : chain[chain.length-1],
		      'accepted' : true}
	    choices.push(choice);
	}
	else {
	    choice = {'venue' : rejected_locations[rejected_locations.length-1],
		      'accepted' : true}
	    choices.push(choice);
	}

	var data = {'chain' : chain,
		    'rejected_locations' : rejected_locations,
		    'user_vector' : current_user_vector,
		    'choices' : choices};
	// Submit
	submitToServer('/api/next_location', data);
    }
}


// Wrapper for the server POST request.
// The returned JSON defines the next location
// and the updated user_vector
function submitToServer(api, data) {

    console.log('Submitting Location To Server: ' + api);
    console.log("Sending data:");
    console.log(data);

    function successfulCallback(data) {
	console.log("Server successfully returned data:");
	console.log(data);

	// Add the new location to the chain
	addToChain(data['location']);

	// Update the current user vector
	current_user_vector = data['user_vector'];
	console.log("Updated user vector:");
	console.log(current_user_vector);
	
	// Create the word bubbles
	var user_words = data['user_words'];
	console.log(user_words);
	var word_list = new Array();
	for(var i=0; i < user_words.length; ++i) {
	    var word_dict = {};
	    if( user_words[i][1]*100 < 2) continue;
	    word_dict['name'] = user_words[i][0];
	    word_dict['word'] = user_words[i][0];
	    word_dict['count'] = 100*user_words[i][1];
	    word_list.push(word_dict);
	}
	console.log("Rendering Bubbles:");
	console.log(word_list);
	d3.select("#vis").select("svg")
	    .remove();
	d3.select("#vis").select("#bubble-labels")
	    .remove();

	word_bubbles = new bubble_plot("#vis", 700, 300);
	word_bubbles.draw(word_list);
	
	$("#venue_list").show();
    }
    
    function errorCallback(data) {
	console.log("Server encountered an error");
	console.log(data);
    }

    clickable = false;

    $.ajax({
	url: api,
	type: "POST",
	dataType: 'json',
	contentType:"application/json; charset=utf-8",
	mimeType : "string",
	data: JSON.stringify(data)
    })
	.done(successfulCallback)
	.fail(errorCallback)
	.always(function() { 
	    console.log("Server transaction complete");

	    clickable = true;
	});
    
    choices.length = 0;

    console.log("Sent 'next_location' request to server. Waiting...");    
}


// Remove the last restaurant from
// the current chain
// Add the last marker to the list of 
function rejectLastPoint() {
    if(clickable == false) {
	console.log("Cannot Click Yet");
	return;
    }

    var last_venue = venue_list.pop();
    console.log("Rejecting last point (length = " + venue_list.length);
    console.log(last_venue);
    last_venue.clear();
    rejected_locations.push(last_venue.data);
}


// Create the google maps MAP
function create_map() {
    var mapOptions = {
	center: new google.maps.LatLng(40.77482, -73.96872),
	zoom: 13,
	mapTypeId: google.maps.MapTypeId.ROADMAP,
	//draggable: false,
	//scrollwheel: false,
	minZoom: 13, maxZoom: 18
    };
    return new google.maps.Map(document.getElementById("map_canvas"), mapOptions);
}


// Load the page! 
$(document).ready(function() {

    $("#venue_list").hide();
    $("#buttons").hide();
    $("#right_column").hide();
    
    // Create the map
    map = create_map();

    // Define clicking on the map
    google.maps.event.addListener(map, 'click', function(event) {
	var latlon = event.latLng;
	beginChain(latlon);
	//$("#address_searchbar_form").css("visibility", "hidden");
	//$("#address_searchbar_form").hide();
    }); 

    // Initialize Bubbles
    // Define clicking on the 'submit' button
    // Send an ajax request to the flask server
    // and get some info
    $("#button_accept").click(function() {
	$("#button_accept").html("Get Next");
	$("#button_try_another").show();
	getNextLocation(true);
    });

    $("#button_try_another").click(function() {
	rejectLastPoint();
	getNextLocation(false);
    });


    $(function() {
        $("#address_searchbar_form input").keypress(function (e) {
	    if ((e.which && e.which == 13) || (e.keyCode && e.keyCode == 13)) {
		var geocoder = new google.maps.Geocoder();
		var address = $("#address_searchbar").val();
		var bounds = new google.maps.LatLngBounds(new google.maps.LatLng(40.69886076226103,
										 -74.02656555175781), 
							  new google.maps.LatLng(40.8826309751934,
										 -73.90296936035156));
		var query = { 'address': address, 'region' : 'US',  'bounds': bounds};
		geocoder.geocode(query, function(results, status) {
		    if (status == google.maps.GeocoderStatus.OK) { 
			console.log("Got location for address: " + address);
			var latlon = results[0]['geometry']['location'];
			beginChain(latlon);
		    }
		    else {
			console.log("Couldn't get location of: " + address);
		    }
		});
		return false;
	    }
	});
    });
    
    $(document).on("click", ".button_remove", function(evt) {
	console.log("Button Click");
	console.log(evt.target);
	var button_id = $(evt.target).attr('id');
	removeVenueWithButtonId(button_id);
    });

});
