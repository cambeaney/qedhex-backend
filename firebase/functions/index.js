const { google } = require('googleapis');
const functions = require('firebase-functions');

const admin = require("firebase-admin");
admin.initializeApp();

const db = admin.firestore();

const axios = require('axios')

function getFreePeriods(events, min_time) {
    events = events.sort((a, b) => {
        return new Date(a['start']['dateTime']) - new Date(b['start']['dateTime']);
    });

    var events_datetime = [];
    events_datetime.push([new Date(), new Date()]);

    events.forEach((event) => {
        events_datetime.push([new Date(event['start']['dateTime']), new Date(event['end']['dateTime'])]);
    });

    var timeMax = new Date();
    timeMax.setHours(24, 0, 0, 0);

    events_datetime.push([timeMax, timeMax]);

    var deltas = [];

    for (i = 0; i < events_datetime.length - 1; i++) {
        var event = events_datetime[i];
        var next_event = events_datetime[i + 1];;

        var delta = (next_event[0] - event[1]) / 1000;

        if (delta > min_time) {
            deltas.push({ 'start': event[1], 'end': next_event[0] });
        }

    }

    return deltas;
}

exports.addWalk = functions.firestore.document('walks/{walkId}')
    .onCreate((snap, context) => {
        const data = snap.data();

        axios.post('http://34.70.169.255/get_route', data)
            .then(res => {
                console.log(res);
                db.collection('walks').doc(snap.id).update({ 'response': res.data });

            })
            .catch(error => {
                db.collection('walks').doc(snap.id).update({ 'response': {'success': false, 'error': error}});
            })

    });

exports.calendarSlot = functions.firestore.document('calendar_slots/{calendarSlotId}')
    .onCreate((snap, context) => {
        const data = snap.data();

        var auth = new google.auth.OAuth2();
        auth.setCredentials({ access_token: data.access_token });

        var min_time = data.min_time;

        if (!min_time) {
            db.collection('calendar_slots').doc(snap.id).update({ 'response': { 'success': false, 'error': 'No min_time parameter specified' } });
        } else {
            const calendar = google.calendar({ version: 'v3', auth });

            var timeMax = new Date();
            timeMax.setHours(24, 0, 0, 0);
    
            calendar.events.list({
                calendarId: 'primary',
                timeMin: (new Date()).toISOString(),
                timeMax: timeMax.toISOString()
            }, (err, res) => {
                if (err) {
                    db.collection('calendar_slots').doc(snap.id).update({ 'response': { 'success': false, 'error': err.message } });
                } else {
                    ret = getFreePeriods(res.data['items'], min_time);
    
                    ret['success'] = true;
    
                    db.collection('calendar_slots').doc(snap.id).update({ 'response': ret });
                }
    
            });
        }

        return 0;
    });

    function ISODateString(d){
        function pad(n){return n<10 ? '0'+n : n}
        return d.getUTCFullYear()+'-'
             + pad(d.getUTCMonth()+1)+'-'
             + pad(d.getUTCDate())+'T'
             + pad(d.getUTCHours())+':'
             + pad(d.getUTCMinutes())+':'
             + pad(d.getUTCSeconds())+'Z'}
       

exports.calendarAdd = functions.firestore.document('calendar_add/{eventId}')
    .onCreate((snap, context) => {
        const data = snap.data();

        var auth = new google.auth.OAuth2();
        auth.setCredentials({ access_token: data.access_token });

        const calendar = google.calendar({ version: 'v3', auth });
         
        if (data['event'] === undefined) {
            db.collection('calendar_add').doc(snap.id).update({ 'response': { 'success': false, 'error': 'No event' } });
        } else {
            data['event']['calendarId'] = 'primary';
            console.log(data);

            calendar.events.insert(data['event'], (err, res) => {
                if (err) {
                    db.collection('calendar_add').doc(snap.id).update({ 'response': { 'success': false, 'error': err.message } });
                } else {
                    db.collection('calendar_add').doc(snap.id).update({ 'response': { 'success': true } });
                }
    
            });
        }

        return 0;
    });