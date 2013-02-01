
// To Do:
/*
  Consider creating a 'location' class that
  stores the following information:
  - Location Dictionary
  - Location Marker
  - Set of path LatLong (from previous location)
  - Marker color, additional info

  And has methods to:
  - populat the path LatLon based on a previous destination
  - Create the marker from the dictionary
*/


// Global Variables
var map = null;
var marker = null;

// The current chain, stored in 
// two arrays.  The first is a dictionary
// of locations, the second is the list
// of google maps markers
var active_chain = false;
var current_path = null;
var current_chain_locations = new Array();
var current_chain_markers = new Array();
var current_chain_latlon = new Array();

var mapOptions = {
    center: new google.maps.LatLng(40.77482, -73.96872),
    zoom: 13,
    mapTypeId: google.maps.MapTypeId.ROADMAP,
    //draggable: false,
    //scrollwheel: false,
    minZoom: 13, maxZoom: 18
};


// Create a twitter bootstrap collapsable
// Object on-th-fly
function createCollapsable(id, title, content) {

    html_string = ' \
	<div class="accordion" id="' + id + '"> \
	 <div class="accordion-group"> \
          <div class="accordion-heading"> \
	    <a class="accordion-toggle" data-toggle="collapse" \
               data-parent="#' + id + '" href="#collapse_' + id + '"> \
	      ' + title + ' \
	    </a> \
	  </div> \
	  <div id="collapse_' + id + '" class="accordion-body collapse"> \
	    <div class="accordion-inner"> \
	      ' + content + ' \
	    </div> \
	  </div> \
	</div> \
      </div>'

    //var htmlObject = $(html_string);
    //return htmlObject;
    return html_string;

}


function addDataToTable(data, columns) {
    
    var table = $("#venue_table");
    var rowCount = $('#venue_table tr').length;
    
    // Create the header, if necessary
    if( rowCount==0 ) {
	// var row = $('<tr></tr>');
	// var row = table.insertRow(0);
	var row = document.createElement("tr");
	for( var column_idx = 0; column_idx < columns.length; ++column_idx ) {
	    var cell = row.insertCell(column_idx);
	    cell.innerHTML = columns[column_idx];
	    cell.setAttribute("class", "table_header");
	}
	table.append(row);
    }
    var rowCount = $('#venue_table tr').length;
    
    var tail_row = createTableRow(data, columns, rowCount-1 );
    table.append(tail_row);
}


function createTableRow(data, columns, row_index) {

    // Recall that the header row is row=0
    var row = document.createElement("tr");

    for( var column_idx = 0; column_idx < columns.length; ++column_idx ) {
	var cell = row.insertCell(column_idx);
	var var_name = columns[column_idx];
	if(var_name != 'review') {
	    cell.innerHTML = data[var_name];
	}
	else {
	    var collapsable = createCollapsable("row_" + row_index, 
						"review", data[var_name]); 
	    cell.innerHTML = collapsable;
	}
	cell.className += "table_column_" + column_idx;
    }
    
    return row;

}


function beginChain(event) {

    // First, check if there is an existing
    // chain.  If so, we kill it.
    if(active_chain==true) {
	clearChain();
    }

    // To be done by clicking
    latlon = event.latLng;
    current_chain_latlon.push(new Array(latlon));
    
    // Create the 'begin' marker
    marker = new google.maps.Marker({
	position: latlon,
	map: map,
	animation: google.maps.Animation.DROP,
	name : "Starting Point"
    });
    current_chain_markers.push(marker);

    // Create a 'location'
    var location = {}; //new Array();
    location['latitude'] = latlon.lat();
    location['longitude'] = latlon.lng();
    current_chain_locations.push(location);
    console.log("Starting Point:");
    console.log(location);

    active_chain = true;

}


// Update the shown path based on the current
// List of LatLon points
function updatePath() {
    var total_chain = new Array();
    for(var i=0; i < current_chain_latlon.length; ++i) {
	total_chain = total_chain.concat(current_chain_latlon[i]);
    }
    current_path.setPath(total_chain);
}


function addToChain(location_dict) {

    console.log("Adding new location:");
    console.log(location_dict);

    current_chain_locations.push(location_dict);

    var lat = location_dict['latitude'];
    var lon = location_dict['longitude'];
    var latlon = new google.maps.LatLng(lat, lon);

    var marker = new google.maps.Marker({
	position: latlon,
	map: map,
	animation: google.maps.Animation.DROP
    });
    current_chain_markers.push(marker);

    // Create the path, including directions
    if( current_path == null ) {
	current_path = new google.maps.Polyline({
	    strokeColor: "#0000FF",
	    strokeOpacity: 0.8,
	    strokeWeight: 4
	});
        current_path.setMap(map);
    }

    // Get the origin
    // Recall, current_chain_latlon is a list of lists
    var last_chain_group = current_chain_latlon[current_chain_latlon.length-1];
    var last_point = last_chain_group[last_chain_group.length-1];

    var service = new google.maps.DirectionsService();
    service.route({
	origin: last_point,
	destination: latlon,
	travelMode: google.maps.DirectionsTravelMode.WALKING
    }, function(result, status) {
	if (status == google.maps.DirectionsStatus.OK) {
	    var new_path = result.routes[0].overview_path;
	    current_chain_latlon.push(new_path);	    
	    updatePath();
	    /*
	    // Concatenate the list of lists into a list
	    var total_chain = new Array();
	    for(var i=0; i < current_chain_latlon.length; ++i) {
		total_chain = total_chain.concat(current_chain_latlon[i]);
	    }
	    //current_chain_latlon = current_chain_latlon.concat(result.routes[0].overview_path);
	    current_path.setPath(total_chain);
	    */
	}
	else {
	    console.log("Travel Directions Error");
	}
    });

    // Append to the table
    addDataToTable(location_dict, ["name", "address", "review"]);

    /* Consier having the path follow streets:
       See: http://stackoverflow.com/questions/10513360/polyline-snap-to-road-using-google-maps-api-v3
*/
/*
    google.maps.event.addListener(map, "click", function(evt) {
	if (path.length == 0) {
	    path.push(evt.latLng);
	    poly = new google.maps.Polyline({ map: map });
	    poly.setPath(path);
	} else {
	    service.route({
		origin: path[path.length - 1],
		destination: evt.latLng,
		travelMode: google.maps.DirectionsTravelMode.DRIVING
	    }, function(result, status) {
		if (status == google.maps.DirectionsStatus.OK) {
		    // path = path.concat(result.routes[0].overview_path);
		    poly.setPath(path);
		}
	    });
	}
    });
*/

}


function clearChain() {

    // Clear the arrays
    for(var i=0; i<current_chain_markers.length; ++i) {
	current_chain_markers[i].setMap(null);
    }

    current_chain_markers.length = 0;
    current_chain_locations.length = 0;
    current_chain_latlon.length = 0;

    // Clear the path
    if( current_path != null ) current_path.setMap(null);
    current_path = null;

    // Clear the table
    $('#venue_table').empty();

    active_chain = false;

}


// SubmitLocationToServer
function submitLocationToServer() {
    console.log('Submitting Location To Server');

    if(active_chain == false) {
	console.log("Cannot submit to server, chain isn't yet active");
	return;
    }
    if( current_chain_locations.length == 0 ) {
	console.log("Invalid chain locations");
	return;
    }

    // var location_data = current_chain_locations[current_chain_locations.length-1];
    // location_data['number_of_locations'] = 1;
    var chain_data = {'chain' : current_chain_locations};
    console.log("Sending data:");
    console.log(chain_data);

    function successfulCallback(data) {
	console.log("Server successfully returned data:");
	console.log(data);
	addToChain(data);
    }
    
    function errorCallback(data) {
	console.log("Server encountered an error");
	console.log(data);
    }

    $.ajax({
	url: "/api/locations",
	type: "POST",
	dataType: 'json',
	contentType:"application/json; charset=utf-8",
	mimeType : "string",
	data: JSON.stringify(chain_data) //location_data
    })
	.done(successfulCallback)
	.fail(errorCallback)
	.always(function() { 
	    console.log("Server transaction complete");
	});
    
    console.log("Sent 'next_location' request to server. Waiting...");    

}


// Remove the last restaurant from
// the current chain
function rejectLastPoint() {

    // Delete the last set of points in the array
    var last_marker = current_chain_markers.pop();
    last_marker.setMap(null);

    // WARNING: 
    // IF THE USER REJECTS THE LAST POINT, WE WANT TO
    // BLACKLIST IT SOMEHOW.  WE'LL NEED TO MAINTAIN
    // SUCH A LIST
    current_chain_locations.pop();
    
    current_chain_latlon.pop();
    updatePath();

    $("#venue_table").find('tr:last').remove();

}

// Load the page! 
$(document).ready(function() {
    
    // Create the map
    map = new google.maps.Map(document.getElementById("map_canvas"), mapOptions);

    // Define clicking on the map
    google.maps.event.addListener(map, 'click', beginChain); 

    // Define clicking on the 'submit' button
    // Send an ajax request to the flask server
    // and get some info
    $("#button_accept").click(submitLocationToServer);
    $("#button_reject").click(rejectLastPoint);

});
