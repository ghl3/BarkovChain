
// Global Variables
var map = null;
var marker = null;
var current_latlong = null;
var current_position = {'latitude' : null, 'longitude' : null};
var location_points = new Array();
var itinerary_path = null;

var mapOptions = {
    center: new google.maps.LatLng(40.7, -74),
    zoom: 12,
    mapTypeId: google.maps.MapTypeId.ROADMAP,
    //draggable: false,
    //scrollwheel: false,
    minZoom: 13, maxZoom: 18
};


// Put the marker on the map
// (creating if necessary)
function placeMarker(map, location) {

    if( marker ){
	marker.setMap(null);
	marker = null;
    }

    // Create if necessary
    if( !marker ){
	marker = new google.maps.Marker({
	    position: location, 
	    map: map,
	    animation: google.maps.Animation.DROP
	});
    }
}

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


// Clear a table and recreate based
// on the input list of data points
function createTableFromData(data, columns) {

    // Create the Table
    var table = document.createElement('table');
    table.setAttribute("class", "table");
    //var table = document.createElement('table');
    //table.setAttribute('id', table_id);

    // Add the Title
    var row = table.insertRow(0);

    // Create the header
    for( var column_idx = 0; column_idx < columns.length; ++column_idx ) {
	var cell = row.insertCell(column_idx);
	cell.innerHTML = columns[column_idx];
	cell.setAttribute("class", "table_header");
    }

    // Add the data rows
    for(var data_itr=0; data_itr<data.length; ++data_itr) {
	var dict = data[data_itr];

	// Recall that the header row is row=0
	var row = table.insertRow(data_itr+1);

	for( var column_idx = 0; column_idx < columns.length; ++column_idx ) {
	    var cell = row.insertCell(column_idx);
	    var var_name = columns[column_idx];
	    if(var_name != 'review') {
		cell.innerHTML = dict[var_name];
	    }
	    else {
		var collapsable = createCollapsable("row_" + data_itr, "review", dict[var_name]); 
		cell.innerHTML = collapsable; //appendChild(collapsable);
	    }
	    cell.className += "table_column_" + column_idx;
	}
    }

    return table;

}


function createPath(data) {

    var coordinates = new Array();

    for(var data_itr=0; data_itr<data.length; ++data_itr) {
	var dict = data[data_itr];
	var lat = dict['latitude'];
	var lon = dict['longitude'];
	var position = new google.maps.LatLng(lat, lon);
	coordinates.push(position);
    }

    /*
    var flightPlanCoordinates = [
        new google.maps.LatLng(37.772323, -122.214897),
        new google.maps.LatLng(21.291982, -157.821856),
        new google.maps.LatLng(-18.142599, 178.431),
        new google.maps.LatLng(-27.46758, 153.027892)
    ];
    */

    // Clear everything in the current points:
    for (var i = 0; i < location_points.length; i++) {
	location_points[i].setMap(null);
    }
    location_points.length = 0;
    if(itinerary_path != null ){
	itinerary_path.setMap(null);
    }


    for(var coor_itr=0; coor_itr < coordinates.length; ++coor_itr) {
	var point = new google.maps.Marker({
	    position: coordinates[coor_itr], //location, 
	    map: map,
	    animation: google.maps.Animation.DROP
	});
	location_points.push(point);
    }

    // Then, add the original node to the
    // list for drawing the path
    coordinates.push(current_latlong);

    itinerary_path = new google.maps.Polyline({
	path: coordinates,
	strokeColor: "#FF0000",
	strokeOpacity: 1.0,
	strokeWeight: 2
    });

    itinerary_path.setMap(map);



    /* Consier having the path follow streets:
       See: http://stackoverflow.com/questions/10513360/polyline-snap-to-road-using-google-maps-api-v3

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
       path = path.concat(result.routes[0].overview_path);
       poly.setPath(path);
       }
       });
       }
       });

    */

}

// SubmitLocationToServer
function submitLocationToServer() {
    console.log('Submitting Location To Server');

    if( current_position['latitude'] == null ) {
	console.log("Current latitude is null");
	return;
    }
    if( current_position['longitude'] == null ) {
	console.log("Current longitude is null");
	return;
    }

    var data = {"longitude" : current_position['longitude'], 
		"latitude" : current_position['latitude'], 
		"number_of_locations" : 3};

    console.log("Sending data:");
    console.log(data);

    function successfulCallback(data) {

	// Add the data to the table
	console.log(data);
	var table = createTableFromData(data, ["name", "address", "review"]);
	$("#venue_list").empty();
	$("#venue_list").append(table);

	// Create a path on the map
	createPath(data);

	console.log("successfulCallback: Table");
	console.log(table);
	//addDataToTable(data, "#venue_list");
	//console.log(data);
    }
    
    function errorCallback(data) {
	console.log(data);
	console.log("Error");
    }

    $.ajax({
	url: "/api/locations",
	dataType: 'json',
	contentType:"application/json; charset=utf-8",
	data: data
    })
	.done(successfulCallback)
	.fail(errorCallback)
	.always(function() { 
	    console.log("Done with 'submitLocationToServer'");
	});
    
    console.log("Sent request to get locations.  Waiting...");    

}


// Load the page! 
$(document).ready(function() {
    
    console.log("Loading Map");
    
    // Create the map
    //var map = new google.maps.Map(document.getElementById("map_canvas"),
    //				  mapOptions);
    map = new google.maps.Map(document.getElementById("map_canvas"), mapOptions);

    // Define clicking on the map
    google.maps.event.addListener(map, 'click', function(event) {
	current_latlong = event.latLng;
	placeMarker(map, event.latLng);
	var lat = marker['position']['Ya'];
	var lon = marker['position']['Za'];
	//console.log(lat);
	//console.log(lon);
	current_position['latitude'] = lat;
	current_position['longitude'] = lon;
	console.log(current_position);
    });
    
    console.log("Loaded Map");

    // Define clicking on the 'submit' button
    // Send an ajax request to the flask server
    // and get some info
    $("#button_accept").click(submitLocationToServer);

    /*
    collapsable = createCollapsable("id", "title", "content");

    $("#test").append(collapsable);
    */

});
