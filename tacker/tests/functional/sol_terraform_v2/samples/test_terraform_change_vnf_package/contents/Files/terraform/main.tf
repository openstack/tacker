resource "aws_instance" "vdu1"{
  ami           = "ami-785db401"
  instance_type = "t2.small"

  tags = {
    Name = "change-vnfpkg-test"
  }
}
