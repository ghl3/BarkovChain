
// Global Variables
var map = null;
var venue_list = new Array();
var current_path = null;
var _lastIndex = 0;
var clickable = false;
var history = new Array();

// Remove this
// var word_bubbles = new bubble_plot("#vis", 700, 300);

function addToHistory(venue, accepted) {

    // Update an entry if it already exists
    var name = venue.data['name'];
    for(var i=0; i < history.length; ++i) {
	if(history[i]['venue']['name'] == name) {
	    history[i]['venue']['accepted'] = accepted
	}
    }
    
    // Else, create it
    var choice = {'venue' : venue.data, 'accepted' : accepted};
    history.push(choice);

}

// Global constants
var manhattan_bounds = new google.maps.LatLngBounds(
    new google.maps.LatLng(40.69886076226103,
			   -74.02656555175781), 
    new google.maps.LatLng(40.8826309751934,
			   -73.90296936035156)
);

var marker_colors = ['CC3300', 'FFCC33', 'FF33CC', '00FFFF', 'FFFFFF', '990066', '006699', 
		     '33FFCC', '99FF66', '336666', 'CC66CC', 'FF6699', '00CC33', '996600', 
		     'FF00FF', '9999CC', '663366', '6699FF', '993333', '99CC99', '0000FF', 
		     'CCFF33', 'FF9966', '66CCCC', '3300CC', '0033CC', '33CC00', 'FFFF00', 
		     '339933', '00FF00', '669900', 'CC9999', 'CCCC66', '333399', '9966FF', 
		     'CC33FF', '660099', '009966']


function createMarker(idx) {
    // http://stackoverflow.com/questions/7095574/google-maps-api-3-custom-marker-color-for-default-dot-marker

    var pinColor = marker_colors[ idx % marker_colors.length];

    var pinImage = new google.maps.MarkerImage("/static/markers/marker_" + pinColor + ".png",
					       new google.maps.Size(21, 34),
					       new google.maps.Point(0,0),
					       new google.maps.Point(10, 34));

    var pinShadow = new google.maps.MarkerImage("/static/markers/map_pin_shadow.png",
						new google.maps.Size(40, 37),
						new google.maps.Point(0, 0),
						new google.maps.Point(12, 35));
    return [pinImage, pinShadow]
}


/**
 * Class venue
 * Stores information about each venue that
 * must be coherent across the pages
 */
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

/**
 * Remove the marker frm the map and
 * remove the row from the table
 */
venue.prototype.clear = function() {
    this.marker.setMap(null);
    if( this.table_row != null ) {
	this.table_row.remove();
    }
}

/**
 * Create a path between the supplied last
 * point and this venue's point using the
 * google Direction api
 * In addition, get the directions as a 
 * string and set them for this venue
 * Call an optional callback
 */
venue.prototype.add_path = function(last_point, callback) {
    var self = this;
    var service = new google.maps.DirectionsService();
    service.route({
	origin: last_point,
	destination: self.latlon,
	travelMode: google.maps.DirectionsTravelMode.WALKING
    }, function(result, status) {
	if (status == google.maps.DirectionsStatus.OK) {
	    var new_path = result.routes[0].overview_path;
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
	    
	    if (callback instanceof Function) { callback(); }
	    return new_path;
	}
	else {
	    console.log("Error: add_path - Google Directions API returned: " + status);
	}
    });
}

/**
 * Return the html id of the table row
 * corresponding to this venue
 */
venue.prototype.table_id = function() {
    if(this.table_row != null) {
	var button = $(this.table_row).find(".button_remove")[0];
	return button.id;
    }
    else {
	return null;
    }
}

/** 
 * Create a twitter bootstrap collapsable
 * It consists of two parts:
 *   - The button that toggles the collapse
 *   - The data section
 * The 'id' input is the idea of the entire block
 * The 'title' is the name on the toggle button
 * The 'content' is the data that gets shown and hidden
 * This function returns an html string
*/
function createCollapsable(id, title, content) {

    var html_string = ' \
<div class="accordion" id="' + id + '"> \
<div class="accordion-group"> \
<div class="accordion-heading"> \
<a class="accordion-toggle" data-toggle="collapse" \
data-parent="#' + id + '" href="#collapse_' + id + '"> \
' + title + ' <span class="caret" style="margin-top: 10px;"></span>\
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

/**
 * Add the current venue to the table
 *
 */
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

    var Description = "<b>New York Magazine Review</b>: <br>"
    Description += data['nymag']['review'];
    Description += '<br> <br> <b>Foursquare Tips:</b> <br> <ul>';
    for(var i=0; i < tips_list.length && i < 5; ++i) {
	Description += "<li>" + tips_list[i]['text'] + "</li>";
    }
    Description += '</ul>';

    var category_string = '';
    if( category_list != null ) {
	for(var i=0; i < category_list.length; ++i) {
	    category_string += category_list[i];
	    if(i != category_list.length-1) {
		category_string += ", ";   
	    }
	}
    }

    var row_html_string = '<div class="venue_row_element row-fluid span12 well" id="row_' + row_index + '">\
\
<div class="span2"><img src="' + this.marker_image.url +'"> </div><div class="span6" style="text-align: left;"><p><strong>' + name + '</strong></p> </div>\
<div class="span3" style="text-align: right;"> \
<button id="button_remove_' + row_index + '" class="button_remove btn btn-small btn-danger">Remove</button> </div> \
<div class="span6" style="text-align: left;"> <p>' + address + '</p> </div> \
<div class="span12">' + category_string + '</div> \
<div class="span12 Description_container"> <div class="Description"> </div> </div>\
</div>';

    // Create the row from the html
    var tail_row = $(row_html_string);

    // Add the collapsable Description
    var collapsable = createCollapsable("row_" + row_index + "_Description", "Description", 
					Description);
    tail_row.find(".Description").html(collapsable);

    table.append(tail_row);
    this.table_row = tail_row;

    $("#venue_list").scrollTop($("#venue_list")[0].scrollHeight);

}


/**
 * Action to take when clicking on delete button
 * Finds the row that owns the button and deletes
 * the venue corresponding to that row, as well
 * as the row itself.
 * Adds this deleted venue to the delete history.
 */
function removeVenueWithButton(button) {

    var button_id = $(button).attr('id');

    console.log("Removing using button id: " + button_id);
    
    for(var i=0; i < venue_list.length; ++i) {
	var this_id = venue_list[i].table_id();
	console.log("Row Id: " + this_id);
	if(venue_list[i].table_id() == button_id) {
	    console.log("Splicing!!!");
	    var venue = venue_list[i];
	    var original_length = venue_list.length;
	    addToHistory(venue, false);
	    venue.clear();
	    venue_list.splice(i, 1);
	    updatePath();

	    // Now, we redo the path between the 
	    // deleted points
	    // Only do if there is a point after
	    // Note that the slice invalidated the
	    // original index
	    console.log("Venue list length: " + venue_list.length + " index: " + i);
	    if( i + 1 < original_length) {
		console.log("Rerouting based on delete");
		venue_list[i].add_path(venue_list[i-1].latlon, 
				       updatePath)
	    }
	    break;
	}
    }
}


/**
 * Reset the state and begin a new chain
 * This is fired when someone enters a beginning
 * location in the search box or when they click
 * on the map.
 * It clears the current chain, resets the state, 
 * and adds a new starting location to the map.
 */
function beginChain(latlon, address) {

    clearChain();
    
    // Create a new path
    current_path = new google.maps.Polyline({
	strokeColor: "#0000FF",
	strokeOpacity: 0.8,
	strokeWeight: 4
    });
    current_path.setMap(map);

    // To be done by clicking
    var data = {};
    data['latitude'] = latlon.lat();
    data['longitude'] = latlon.lng();
    data['initial'] = true;

    // Create the new object
    var initial_location = new venue(data);
    venue_list.push(initial_location);

    // Change the state
    clickable = true;
    $("#buttons").css("visibility", "visible");
    $("#button_initial").show();
    $("#button_accept").hide();
    $("#button_try_another").hide();
    $("#instruction_content").html("Enter another address or click the map to start a new chain");

    // Add the initial location
    $("#starting_point_img").attr("src", initial_location.marker_image.url);

    // Reverse Geocode
    if( address != null ) {
	$("#initial_address").html(address);
    } else {
	
	var geocoder = new google.maps.Geocoder();
	var starting_point_query = {'latLng': latlon};
	geocoder.geocode(starting_point_query, function(results, status) {
            if (status == google.maps.GeocoderStatus.OK) {
		if (results[1]) {
		    $("#initial_address").html(results[1].formatted_address);
		} else {
		    alert('No results found');
		}
	    } else {
		alert('Geocoder failed due to: ' + status);
	    }
	});
    }

    $("#starting_point_container").css("visibility", "visible");
    
    return;

}


/**
 * Create a new path line on the map
 * basedUpdate the shown path based on the current
 * List of LatLon points
 */
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


/**
 * Add a new location to the venue list
 * from a dictionary returned by the
 * server.
 */
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

}


/**
 * Remove all venues from the chain,
 * hide the buttons and the starting
 * point marker, and the venue list;
 *
 */
function clearChain() {

    // Clear the array
    for(var i=0; i < venue_list.length; ++i) {
	venue_list[i].clear();
    }
    venue_list.length = 0;
    history.length = 0;
    _lastIndex = 0;

    if( current_path != null ) current_path.setMap(null);
    current_path = null;

    d3.select("#vis").select("svg")
	.remove();
    d3.select("#vis").select("#bubble-labels")
	.remove();

    $("#buttons").css("visibility", "hidden");
    $("#starting_point_container").css("visibility", "hidden");
    $("#venue_list").hide();
    $("#right_column").hide();
    $("#waiting").css("visibility", "hidden");
    return;

}


/**
 * Get the initial location in the chain.
 * The initial location is not based on semantic
 * similairty since it has no previous choices
 * to compare to.
*/
function getInitialLocation() {

    if(clickable == false) {
	console.log("Cannot Click Yet");
	return;
    }

    if( venue_list.length == 0 ) {
	console.log("Error: No venues exist yet");
	return;
    }

    var data = {'location' : venue_list[0].data}
    submitToServer('/api/initial_location', data);
}


/**
 * Get the next 'location' from the server
 * based on the current location, reviews, 
 * and the past history of locations.
*/
function getNextLocation() {

    if(clickable == false) {
	console.log("Cannot Click Yet");
	return;
    }
    
    if( venue_list.length == 0 ) {
	console.log("Error: No venues exist yet");
	return;
    }

    var venue_chain = new Array();
    for( var i = 0; i < venue_list.length; ++i) {
	venue_chain.push(venue_list[i].data);
    }
    
    var data = {'chain' : venue_chain,
		'history' : history};

    submitToServer('/api/next_location', data);
}


/** 
 * Get the next location from the server by
 * creating a jquery ajax POST request that
 * includes all the necessary information in
 * its body.
 * Update the current vector based on the
 * return value.
 */
function submitToServer(api, data) {

    // Ensure one can't click twice
    clickable = false;
    $("#waiting").css("visibility", "visible");

    console.log('Submitting Location To Server: ' + api);
    console.log("Sending data:");
    console.log(data);

    function successfulCallback(data) {
	console.log("Server successfully returned data:");
	console.log(data);

	// Add the new location to the chain
	addToChain(data['location']);

	// Update the current user vector
	//current_user_vector = data['user_vector'];
	//console.log("Updated user vector:");
	//console.log(current_user_vector);
	
	// Create the word bubbles
	/*
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
	*/
	$("#venue_list").show();
	$("#button_accept").show();
	$("#button_try_another").show();
	$("#button_initial").hide();
	$("#right_column").show();
    }
    
    function errorCallback(data) {
	console.log("Server encountered an error");
	console.log(data);
    }

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
	    $("#waiting").css("visibility", "hidden");
	});
    
    console.log("Sent 'next_location' request to server. Waiting...");    
}

/**
 * Take the contents of the searchbar
 * and find the address (within manhattan)
 * and drop a pin on that address as the
 * starting point.
 */
function searchbarInput(e) {
    if ((e.which && e.which == 13) || (e.keyCode && e.keyCode == 13)) {
	var geocoder = new google.maps.Geocoder();
	var address = $("#address_searchbar").val();
	$("#address_searchbar").val('');
	var query = { 'address': address, 'region' : 'US',  'bounds': manhattan_bounds};
	geocoder.geocode(query, function(results, status) {
	    if (status == google.maps.GeocoderStatus.OK) { 
		console.log("Got location for address: " + address);
		var latlon = results[0]['geometry']['location'];
		beginChain(latlon, address);
		map.setCenter(latlon);
	    }
	    else {
		console.log("Couldn't get location of: " + address);
	    }
	});
	return false;
    }
}


/**
 * Create a new google maps object
 */
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


/**
 * Start the page
 */
$(document).ready(function() {

    clearChain();

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
    $("#button_initial").click(function() {
	getInitialLocation(true);
    });

    $("#button_accept").click(function() {
	if( venue_list.length > 1 ) {
	    addToHistory(venue_list[venue_list.length-1], true);
	}
	getNextLocation();
    });

    $("#button_try_another").click(function() {
	if( venue_list.length > 1 ) {
	    var last_venue = venue_list.pop();
	    last_venue.clear();
	    addToHistory(last_venue, false);
	}
	console.log("Trying Another - History:");
	console.log(history);
	getNextLocation();
    });

    $("#address_searchbar_form input").keypress(searchbarInput); 

    $(document).on("click", ".button_remove", function(evt) {
	console.log("Button Click");
	console.log(evt.target);
	removeVenueWithButton(evt.target);
    });

});
