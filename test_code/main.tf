terraform { 
  cloud { 
    hostname = "tfe3.munnep.com" 
    organization = "test" 

    workspaces { 
      name = "test" 
    } 
  } 
}

resource "null_resource" "name" {
  
}