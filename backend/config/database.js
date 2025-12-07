const mongoose = require('mongoose');
require('dotenv').config();

exports.connectDB = () => {
    // CHANGED: specifically use MONGODB_URL to match the OpenShift/Docker config
    mongoose.connect(process.env.MONGODB_URL, {
        useNewUrlParser: true,
        useUnifiedTopology: true
    })
    .then(() => {
        console.log('✅ Database connected successfully');
    })
    .catch(error => {
        console.log(`❌ Error while connecting server with Database`);
        console.log(error);
        process.exit(1);
    })
};