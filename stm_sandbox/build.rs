 use std::env;  
 use copy_to_output::copy_to_output;  
   
 fn main() {  
     copy_to_output(
         "acconeer", 
         &env::var("PROFILE").unwrap()
    )
        .expect("Failed to copy acconeer code");  
 }
