resource "aws_instance" "vdu1"{
  ami           = "ami-785db401"
  instance_type = "t2.micro"

  tags = {
    Name = "hoge01"
  }
}
