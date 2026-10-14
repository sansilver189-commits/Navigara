// Twilio Function: places a call ONLY if the dashboard signed the request.
//
// Paste this into a Twilio Function (path /dial, visibility "Protected") and add an
// environment variable DIAL_SECRET with the same value as DIAL_SECRET in your .env file.
// "Protected" makes Twilio check its own signature on every request to this Function.
const crypto = require('crypto');

exports.handler = function (context, event, callback) {
  const twiml = new Twilio.twiml.VoiceResponse();
  const deny = (why) => { console.log('Refused: ' + why); twiml.say('This call is not allowed.'); callback(null, twiml); };

  const parts = String(event.ticket || '').split('.');
  if (parts.length !== 2 || !context.DIAL_SECRET) return deny('missing ticket or secret');
  const [body, sig] = parts;
  const expected = crypto.createHmac('sha256', context.DIAL_SECRET).update(body).digest('base64url');
  if (sig.length !== expected.length || !crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected))) {
    return deny('bad signature');
  }
  let t;
  try { t = JSON.parse(Buffer.from(body, 'base64url').toString('utf8')); } catch (e) { return deny('bad ticket'); }
  if (!t.exp || t.exp < Date.now() / 1000) return deny('ticket expired');
  if (!/^\+[1-9]\d{7,14}$/.test(t.to || '') || !/^\+[1-9]\d{7,14}$/.test(t.from || '')) return deny('bad number');

  // answerOnBridge: the browser only shows "connected" once the other side really picks up.
  const dial = twiml.dial({ callerId: t.from, answerOnBridge: true, timeout: 30 });
  dial.number(t.to);
  callback(null, twiml);
};
